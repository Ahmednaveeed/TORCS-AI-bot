import msgParser
import carState
import carControl
import numpy as np
import joblib
import pandas as pd
from tensorflow.keras.models import load_model

class Driver(object):
    def __init__(self, stage):
        self.WARM_UP = 0
        self.QUALIFYING = 1
        self.RACE = 2
        self.UNKNOWN = 3
        self.stage = stage
        
        self.parser = msgParser.MsgParser()
        self.state = carState.CarState()
        self.control = carControl.CarControl()
        
        self.steer_lock = 0.785398
        self.max_speed = 100
        self.prev_rpm = None
        
        # Initialize gear to 1 (first gear) to ensure the car can move
        self.control.gear = 1
        
        # Load the new trained Keras model and scaler
        self.model = load_model('sample_model.h5')
        self.scaler = joblib.load('scaler.save')
        
        # Define feature names matching the training dataset
        self.feature_names = [
            'Angle', 'DistanceCovered', 'LastLapTime',
            'Opponent_1', 'Opponent_2', 'Opponent_3', 'Opponent_4', 'Opponent_5', 'Opponent_6',
            'Opponent_7', 'Opponent_8', 'Opponent_9', 'Opponent_10', 'Opponent_11', 'Opponent_12',
            'Opponent_13', 'Opponent_14', 'Opponent_15', 'Opponent_16', 'Opponent_17', 'Opponent_18',
            'Opponent_19', 'Opponent_20', 'Opponent_21', 'Opponent_22', 'Opponent_23', 'Opponent_24',
            'Opponent_25', 'Opponent_26', 'Opponent_27', 'Opponent_28', 'Opponent_29', 'Opponent_30',
            'Opponent_31', 'Opponent_32', 'Opponent_33', 'Opponent_34', 'Opponent_35', 'Opponent_36',
            'RPM', 'SpeedX', 'SpeedY', 'SpeedZ',
            'Track_1', 'Track_2', 'Track_3', 'Track_4', 'Track_5', 'Track_6', 'Track_7', 'Track_8', 'Track_9',
            'Track_10', 'Track_11', 'Track_12', 'Track_13', 'Track_14', 'Track_15', 'Track_16', 'Track_17', 'Track_18', 'Track_19',
            'TrackPosition', 'WheelSpinVelocity_1', 'WheelSpinVelocity_2', 'WheelSpinVelocity_3', 'WheelSpinVelocity_4', 'Z'
        ]

    def init(self):
        self.angles = [0 for x in range(19)]
        for i in range(5):
            self.angles[i] = -90 + i * 15
            self.angles[18 - i] = 90 - i * 15
        for i in range(5, 9):
            self.angles[i] = -20 + (i-5) * 5
            self.angles[18 - i] = 20 - (i-5) * 5
        return self.parser.stringify({'init': self.angles})

    def drive(self, msg):
        self.state.setFromMsg(msg)
        
        # Extract features matching the training dataset
        opponents = self.state.opponents if self.state.opponents else [1.0] * 36
        track = self.state.track if self.state.track else [0.0] * 19
        wheelSpinVel = self.state.wheelSpinVel if self.state.wheelSpinVel else [0.0] * 4
        
        features = [
            self.state.angle or 0.0,
            self.state.distRaced or 0.0,
            self.state.lastLapTime or 0.0
        ] + opponents + [
            self.state.rpm or 0.0,
            self.state.speedX or 0.0,
            self.state.speedY or 0.0,
            self.state.speedZ or 0.0
        ] + track + [
            self.state.trackPos or 0.0
        ] + wheelSpinVel + [
            self.state.z or 0.0
        ]
        
        # Log some input features to debug
        print(f"Input Features - Angle: {self.state.angle or 0.0:.4f}, DistRaced: {self.state.distRaced or 0.0:.4f}, TrackPos: {self.state.trackPos or 0.0:.4f}")
        
        if len(features) != len(self.feature_names):
            raise ValueError(f"Feature length {len(features)} does not match expected {len(self.feature_names)}")
        
        # Convert to DataFrame and scale
        features_df = pd.DataFrame([features], columns=self.feature_names)
        features_scaled = self.scaler.transform(features_df)
        
        # Predict actions with verbose=0 to suppress progress bars
        predictions = self.model.predict(features_scaled, batch_size=1, verbose=0)
        accel, brake, clutch, steer = predictions[0]
        
        # Scale predictions to ensure accel is impactful
        accel = accel * 2.0
        brake = brake * 2.0
        clutch = clutch * 2.0
        steer = steer * 2.0
        
        # Set control attributes
        self.control.accel = np.clip(accel, 0, 1)
        self.control.brake = np.clip(brake, 0, 1)
        self.control.clutch = np.clip(clutch, 0, 1)
        self.control.steer = np.clip(steer, -1, 1)
        
        # Gear logic: Simplified to keep gear in forward (1 to 6)
        if self.state.rpm and self.state.rpm > 9000 and self.control.gear < 6:
            self.control.gear += 1
            print(f"Upshifted to gear: {self.control.gear}")
        elif self.state.rpm and self.state.rpm < 3000 and self.control.gear > 1:
            self.control.gear -= 1
            print(f"Downshifted to gear: {self.control.gear}")
        # Force gear to 1 if in reverse or neutral
        if self.control.gear <= 0:
            self.control.gear = 1
            print(f"Forced gear to 1 (was {self.control.gear})")
        
        return self.control.toMsg()
    
    def onShutDown(self):
        pass
    
    def onRestart(self):
        pass