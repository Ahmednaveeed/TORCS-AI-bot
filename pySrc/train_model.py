import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam
import joblib

# Load dataset
data_path = 'DirtTrack.csv'  # Updated to use the new dataset
df = pd.read_csv(data_path)

# Strip any whitespace from column names
df.columns = df.columns.str.strip()

# Define columns to exclude (matching your dataset)
cols_to_del = ['DistanceFromStart', 'FuelLevel', 'Gear', 'CurrentLapTime', 'Damage', 'RacePosition']

# Drop unnecessary columns
df = df.drop(columns=cols_to_del)

# Define feature and target columns
feature_columns = [
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
target_columns = ['Acceleration', 'Braking', 'Clutch', 'Steering']

# Verify all feature and target columns exist
missing_cols = [col for col in feature_columns + target_columns if col not in df.columns]
if missing_cols:
    raise ValueError(f"Missing columns in dataset: {missing_cols}")

# Split features and targets
X = df[feature_columns]
y = df[target_columns]

# Split into training and validation sets
X_train, X_val, y_train, y_val = train_test_split(X, y, train_size=0.8, random_state=42)

# Scale features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)

# Save scaler
joblib.dump(scaler, 'new_scaler.save')  # New scaler file to avoid overwriting existing scaler.save

# Define model architecture
model = Sequential([
    Dense(1024, input_shape=(X_train.shape[1],), activation='relu', kernel_initializer='he_normal'),
    Dense(512, activation='relu', kernel_initializer='he_normal'),
    Dense(256, activation='relu', kernel_initializer='he_normal'),
    Dense(128, activation='relu', kernel_initializer='he_normal'),
    Dense(64, activation='relu', kernel_initializer='he_normal'),
    Dense(32, activation='relu', kernel_initializer='he_normal'),
    Dense(16, activation='relu', kernel_initializer='he_normal'),
    Dense(8, activation='relu', kernel_initializer='he_normal'),
    Dense(4, kernel_initializer='he_normal')  # Output: Acceleration, Braking, Clutch, Steering
])

# Compile model
learning_rate = 3e-3
model.compile(optimizer=Adam(learning_rate=learning_rate), loss='mean_squared_error', metrics=['mae'])

# Train model
model.fit(
    X_train_scaled, y_train,
    validation_data=(X_val_scaled, y_val),
    batch_size=256,
    epochs=100,
    verbose=1
)

# Save model
model.save('new_sample_model.h5')  # New model file to avoid overwriting sample_model.h5

# Evaluate model
val_loss, val_mae = model.evaluate(X_val_scaled, y_val, verbose=0)
print(f"Validation Loss: {val_loss:.4f}, Validation MAE: {val_mae:.4f}")