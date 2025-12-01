import os
import json
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash, session, jsonify
from werkzeug.utils import secure_filename
from flask_login import login_user, logout_user, login_required, current_user
from app.ml.model import FoodClassifier
from app.models import User, FoodLog, WaterLog, ExerciseLog
from app import login_manager, oauth

main = Blueprint('main', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.objects(pk=user_id).first()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

# --- Google Auth ---
@main.route('/google/login')
def google_login():
    redirect_uri = url_for('main.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@main.route('/google/callback')
def google_callback():
    token = oauth.google.authorize_access_token()
    user_info = token.get('userinfo')
    
    if not user_info:
        flash("Google Login Failed")
        return redirect(url_for('main.login'))
        
    email = user_info.get('email')
    name = user_info.get('name') or email.split('@')[0]
    
    # Check if user exists
    user = User.objects(username=email).first()
    
    if not user:
        # Create new user
        user = User(
            username=email,
            password='google_oauth_dummy_password', # They won't use password login anyway
            height=175, weight=70, age=25,
            goal_calories=2000
        )
        user.save()
        flash(f"Account created for {name}!")
    
    login_user(user)
    return redirect(url_for('main.dashboard'))

# --- Auth Routes ---
@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check if exists
        if User.objects(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('main.register'))
            
        # Create User
        new_user = User(
            username=username,
            password=password, # In production, hash this!
            height=175, weight=70, age=25, # Defaults
            goal_calories=2000
        )
        new_user.save()
        login_user(new_user)
        return redirect(url_for('main.profile')) # Go to profile to set stats
        
    return render_template('register.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.objects(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@main.route('/stats')
@login_required
def stats():
    # Get last 7 days
    end_date = date.today()
    start_date = end_date - timedelta(days=6)
    
    # Fetch logs
    logs = FoodLog.objects(user=current_user, date_posted__gte=start_date)
    
    # Process Data for Chart
    data = {}
    # Init last 7 days with 0
    for i in range(7):
        day = start_date + timedelta(days=i)
        data[day.strftime('%Y-%m-%d')] = 0
        
    for log in logs:
        day_str = log.date_posted.strftime('%Y-%m-%d')
        if day_str in data:
            data[day_str] += log.calories
            
    labels = list(data.keys())
    values = list(data.values())
    
    return render_template('stats.html', labels=labels, values=values, user=current_user)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

# --- Dashboard ---
@main.route('/')
@login_required
def dashboard():
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    
    # Fetch separate logs
    todays_food = FoodLog.objects(user=current_user, date_posted__gte=today_start, date_posted__lte=today_end)
    todays_exercise = ExerciseLog.objects(user=current_user, date_posted__gte=today_start, date_posted__lte=today_end)
    
    # Calculations
    cals_eaten = sum(f.calories for f in todays_food)
    cals_burned = sum(e.calories_burned for e in todays_exercise)
    net_cals = cals_eaten - cals_burned
    remaining_cals = current_user.goal_calories - net_cals
    
    total_protein = sum(f.protein for f in todays_food if f.protein)
    todays_water = WaterLog.objects(user=current_user, date_posted__gte=today_start, date_posted__lte=today_end).count()
    
    return render_template('dashboard.html', 
                           user=current_user,
                           cals_eaten=cals_eaten,
                           cals_burned=cals_burned,
                           net_cals=net_cals,
                           remaining=remaining_cals,
                           protein=total_protein,
                           water=todays_water,
                           food_log=todays_food,
                           exercise_log=todays_exercise)

# --- Chat ---
@main.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    user_message = data.get('message')
    
    # Build Context
    context = f"User is {current_user.weight}kg, Goal: {current_user.goal_calories}kcal. Activity: {current_user.activity_level}."
    
    data_path = os.path.join(current_app.root_path, '..', 'data', 'calories.json')
    classifier = FoodClassifier(data_path)
    response = classifier.chat_with_coach(user_message, context)
    
    # Execute Actions
    action = response.get('action')
    action_data = response.get('data', {})
    
    if action == 'update_goal':
        if 'goal_calories' in action_data:
            current_user.goal_calories = int(action_data['goal_calories'])
            current_user.save()
            
    elif action == 'log_food':
        # Log the food automatically
        new_food = FoodLog(
            user=current_user,
            name=action_data.get('food_name', 'Quick Add'),
            calories=action_data.get('calories', 0),
            protein=action_data.get('protein', 0),
            carbs=0, fat=0 # AI might skip these for simple chat logs
        )
        new_food.save()
        
    return json.dumps(response)

# --- Deletion Routes ---
@main.route('/delete_food/<id>')
@login_required
def delete_food(id):
    FoodLog.objects(pk=id).delete()
    return redirect(url_for('main.dashboard'))

@main.route('/delete_exercise/<id>')
@login_required
def delete_exercise(id):
    ExerciseLog.objects(pk=id).delete()
    return redirect(url_for('main.dashboard'))

# --- Actions ---
@main.route('/add_water')
@login_required
def add_water():
    new_water = WaterLog(user=current_user)
    new_water.save()
    
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    count = WaterLog.objects(user=current_user, date_posted__gte=today_start, date_posted__lte=today_end).count()
    print(f"Water Added. New Count: {count}")
    
    return jsonify({'success': True, 'water': count, 'goal': current_user.goal_water})

@main.route('/remove_water')
@login_required
def remove_water():
    today_start = datetime.combine(date.today(), datetime.min.time())
    latest = WaterLog.objects(user=current_user, date_posted__gte=today_start).order_by('-date_posted').first()
    if latest:
        latest.delete()
    
    today_end = datetime.combine(date.today(), datetime.max.time())
    count = WaterLog.objects(user=current_user, date_posted__gte=today_start, date_posted__lte=today_end).count()
    print(f"Water Removed. New Count: {count}")
    
    return jsonify({'success': True, 'water': count, 'goal': current_user.goal_water})

@main.route('/manual_add', methods=['GET', 'POST'])
@login_required
def manual_add():
    if request.method == 'POST':
        text = request.form.get('food_text')
        data_path = os.path.join(current_app.root_path, '..', 'data', 'calories.json')
        classifier = FoodClassifier(data_path)
        result = classifier.estimate_from_text(text)
        
        if result:
            session['temp_food'] = result
            return redirect(url_for('main.advisor'))
        else:
            flash("Could not understand food.")
    return render_template('manual_add.html')

@main.route('/predict', methods=['POST'])
@login_required
def predict():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return redirect(url_for('main.dashboard'))
        
    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    data_path = os.path.join(current_app.root_path, '..', 'data', 'calories.json')
    classifier = FoodClassifier(data_path)
    result = classifier.predict(filepath)
    
    result['image_file'] = filename
    session['temp_food'] = result
    return redirect(url_for('main.advisor'))

@main.route('/advisor', methods=['GET', 'POST'])
@login_required
def advisor():
    food_data = session.get('temp_food')
    if not food_data:
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'eat':
            nut = food_data['nutrition']
            # Handle manual vs AI structure
            if isinstance(nut, dict):
                c = nut.get('calories', 0)
                p = nut.get('protein', 0)
                cb = nut.get('carbs', 0)
                f = nut.get('fat', 0)
            else:
                c, p, cb, f = 0, 0, 0, 0

            new_food = FoodLog(
                user=current_user,
                name=food_data['dish'],
                calories=c, protein=p, carbs=cb, fat=f,
                image_file=food_data.get('image_file')
            )
            new_food.save()
            session.pop('temp_food', None)
            return redirect(url_for('main.dashboard'))
        else:
            session.pop('temp_food', None)
            return redirect(url_for('main.dashboard'))

    # Precise Calculation (Matches Dashboard)
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    
    todays_food = FoodLog.objects(user=current_user, date_posted__gte=today_start, date_posted__lte=today_end)
    todays_exercise = ExerciseLog.objects(user=current_user, date_posted__gte=today_start, date_posted__lte=today_end)
    
    cals_eaten = sum(f.calories for f in todays_food)
    cals_burned = sum(e.calories_burned for e in todays_exercise)
    
    # Remaining = Goal - (Eaten - Burned)
    remaining_before = current_user.goal_calories - (cals_eaten - cals_burned)
    
    # Check safety
    this_food_cals = food_data['nutrition'].get('calories', 0)
    safe = this_food_cals <= remaining_before
    
    return render_template('advisor.html', food=food_data, remaining=remaining_before, safe=safe)

@main.route('/workout', methods=['GET', 'POST'])
@login_required
def workout():
    if request.method == 'POST':
        activity = request.form.get('activity')
        duration = int(request.form.get('duration'))
        burned = int(request.form.get('calories')) 
        
        log = ExerciseLog(
            user=current_user,
            activity_name=activity,
            duration_minutes=duration,
            calories_burned=burned
        )
        log.save()
        return redirect(url_for('main.dashboard'))

    # Load Gym Data
    gym_data = {}
    try:
        data_path = os.path.join(current_app.root_path, '..', 'data', 'gym_exercises.json')
        with open(data_path, 'r') as f:
            gym_data = json.load(f)
    except:
        pass
        
    return render_template('workout.html', gym_data=gym_data, user_weight=current_user.weight)

@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # CASE 1: Body Analysis Upload
        if 'file' in request.files and request.files['file'].filename != '':
            try:
                file = request.files['file']
                filename = secure_filename(file.filename)
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # AI Analysis
                data_path = os.path.join(current_app.root_path, '..', 'data', 'calories.json')
                classifier = FoodClassifier(data_path)
                stats = classifier.analyze_body(filepath)
                
                if stats:
                    # Auto-Update User Stats
                    current_user.gender = stats.get('gender', 'Male')
                    current_user.height = float(stats.get('height', 175))
                    current_user.weight = float(stats.get('weight', 70))
                    
                    # Auto-Recalculate Goal (Mifflin-St Jeor)
                    # We assume age 25 if not set, and Moderate activity
                    age = current_user.age if current_user.age else 25
                    activity = current_user.activity_level if current_user.activity_level else 'Moderate'
                    
                    bmr = (10 * current_user.weight) + (6.25 * current_user.height) - (5 * age)
                    if current_user.gender == 'Male':
                        bmr += 5
                    else:
                        bmr -= 161
                    
                    multipliers = {'Sedentary': 1.2, 'Light': 1.375, 'Moderate': 1.55, 'Active': 1.725}
                    tdee = int(bmr * multipliers.get(activity, 1.55))
                    
                    # Auto-Calculate Water (35ml per kg / 250ml per glass)
                    water_glasses = int((current_user.weight * 35) / 250)
                    
                    current_user.goal_calories = tdee
                    current_user.goal_water = water_glasses
                    current_user.save()
                    
                    flash(f"AI Analysis Success! Goal: {tdee} kcal, Water: {water_glasses} glasses.")
                else:
                    flash("AI could not detect a person clearly. Please try a full-body shot.")
                
                return redirect(url_for('main.profile'))
                
            except Exception as e:
                flash(f"Analysis Error: {e}")
                return redirect(url_for('main.profile'))

        # CASE 2: Manual Form Save
        try:
            # Check if form has data before converting
            if not request.form.get('weight'):
                # If we got here but weight is missing, it was a phantom post or error
                return render_template('profile.html', user=current_user)

            weight = float(request.form.get('weight'))
            height = float(request.form.get('height'))
            age = int(request.form.get('age'))
            gender = request.form.get('gender')
            activity = request.form.get('activity')
            
            # Mifflin-St Jeor Equation
            bmr = (10 * weight) + (6.25 * height) - (5 * age)
            if gender == 'Male':
                bmr += 5
            else:
                bmr -= 161
                
            multipliers = {
                'Sedentary': 1.2,
                'Light': 1.375,
                'Moderate': 1.55,
                'Active': 1.725
            }
            tdee = int(bmr * multipliers.get(activity, 1.2))
            
            # Water Goal: 35ml per kg
            water_glasses = int((weight * 35) / 250)
            
            current_user.weight = weight
            current_user.height = height
            current_user.age = age
            current_user.gender = gender
            current_user.activity_level = activity
            current_user.goal_calories = tdee 
            current_user.goal_water = water_glasses
            current_user.save()
            flash(f'Updated! Calorie Goal: {tdee}, Water Goal: {water_glasses}')
            
        except Exception as e:
            flash(f'Error updating stats: {e}')
            
    return render_template('profile.html', user=current_user)
