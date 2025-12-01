from flask_login import UserMixin
import mongoengine as db
from datetime import datetime

class User(UserMixin, db.Document):
    username = db.StringField(max_length=150, unique=True, required=True)
    password = db.StringField(max_length=150, required=True)
    
    # Physical Stats
    height = db.FloatField() # in cm
    weight = db.FloatField() # in kg
    age = db.IntField()
    gender = db.StringField(max_length=10) 
    activity_level = db.StringField(max_length=20)
    
    # Goals
    goal_calories = db.IntField(default=2000)
    goal_protein = db.IntField(default=150)
    goal_water = db.IntField(default=8) 

    # Meta for Flask-Login
    def get_id(self):
        return str(self.id)

class FoodLog(db.Document):
    user = db.ReferenceField(User, reverse_delete_rule=db.CASCADE)
    name = db.StringField(max_length=100, required=True)
    calories = db.IntField(required=True)
    protein = db.FloatField()
    carbs = db.FloatField()
    fat = db.FloatField()
    image_file = db.StringField(max_length=100)
    date_posted = db.DateTimeField(default=datetime.now)

class WaterLog(db.Document):
    user = db.ReferenceField(User, reverse_delete_rule=db.CASCADE)
    amount = db.IntField(default=1) # 1 glass
    date_posted = db.DateTimeField(default=datetime.now)

class ExerciseLog(db.Document):
    user = db.ReferenceField(User, reverse_delete_rule=db.CASCADE)
    activity_name = db.StringField(max_length=100, required=True)
    duration_minutes = db.IntField(required=True)
    calories_burned = db.IntField()
    date_posted = db.DateTimeField(default=datetime.now)
