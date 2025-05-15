import msgParser

class CarControl(object):
    '''
    An object holding all the control parameters of the car
    '''
    # TODO range check on set parameters

    def __init__(self, accel = 0.0, brake = 0.0, gear = 1, steer = 0.0, clutch = 0.0, focus = 0, meta = 0):
        '''Constructor'''
        self.parser = msgParser.MsgParser()
        
        self.actions = None
        
        self.accel = accel
        self.brake = brake
        self.gear = gear
        self.steer = steer
        self.clutch = clutch
        self.focus = focus
        self.meta = meta
    
    def toMsg(self):
        '''
        Convert control parameters to a string message for TORCS
        '''
        self.actions = {
            'accel': [self.accel],
            'brake': [self.brake],
            'gear': [self.gear],
            'steer': [self.steer]
        }
        return self.parser.stringify(self.actions)