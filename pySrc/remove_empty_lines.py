import pandas as pd
df = pd.read_csv('DirtTrack.csv')
print(df[['Acceleration', 'Braking', 'Clutch', 'Steering']].describe())