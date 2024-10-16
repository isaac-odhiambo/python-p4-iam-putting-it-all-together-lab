from flask import request, session, jsonify
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError
from config import app, db, api
from models import User, Recipe

class ClearSession(Resource):
    def delete(self):
        session.pop('user_id', None)
        return {}, 204

class Signup(Resource):
    def post(self):
        json = request.get_json()
        username = json.get('username')
        password = json.get('password')
        image_url = json.get('image_url', '')  # Optional
        bio = json.get('bio', '')  # Optional

        errors = {}

        if not username:
            errors['username'] = 'Username is required.'
        if not password:
            errors['password'] = 'Password is required.'

        if errors:
            return {'errors': errors}, 422

        user = User(username=username)
        user.password_hash = password
        user.image_url = image_url
        user.bio = bio

        try:
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            return {
                'id': user.id,
                'username': user.username,
                'image_url': user.image_url,
                'bio': user.bio
            }, 201
        except IntegrityError:
            db.session.rollback()
            return {'errors': {'username': 'Username already exists.'}}, 422

class CheckSession(Resource):
    def get(self):
        user_id = session.get('user_id')
        if user_id:
            user = db.session.get(User, user_id)
            if user:
                return user.to_dict(), 200
        return {'error': 'Unauthorized'}, 401

class Login(Resource):
    def post(self):
        json = request.get_json()
        user = User.query.filter_by(username=json['username']).first()
        if user and user.authenticate(json['password']):
            session['user_id'] = user.id
            return user.to_dict(), 200
        return {'error': 'Invalid credentials'}, 401

class Logout(Resource):
    def delete(self):
        if 'user_id' not in session:
            return {'error': 'Unauthorized'}, 401
        session.pop('user_id', None)
        return {}, 204

class RecipeIndex(Resource):
    def get(self):
        user_id = session.get('user_id')
        if not user_id:
            return {'error': 'Unauthorized'}, 401
            
        recipes = Recipe.query.filter_by(user_id=user_id).all()
        return [recipe.to_dict() for recipe in recipes], 200

    def post(self):
        user_id = session.get('user_id')
        if not user_id:
            return {'error': 'Unauthorized'}, 401
            
        json_data = request.get_json()
        title = json_data.get('title')
        instructions = json_data.get('instructions')
        minutes_to_complete = json_data.get('minutes_to_complete')

        if not title or not instructions or minutes_to_complete is None:
            return {'error': 'Invalid data'}, 422

        try:
            new_recipe = Recipe(
                title=title,
                instructions=instructions,
                minutes_to_complete=minutes_to_complete,
                user_id=user_id
            )
            db.session.add(new_recipe)
            db.session.commit()
            return new_recipe.to_dict(), 201
        except ValueError as e:
            db.session.rollback()
            return {'errors': {'instructions': str(e)}}, 422

# Register the API resources
api.add_resource(ClearSession, '/clear', endpoint='clear')
api.add_resource(Signup, '/signup', endpoint='signup')
api.add_resource(CheckSession, '/check_session', endpoint='check_session')
api.add_resource(Login, '/login', endpoint='login')
api.add_resource(Logout, '/logout', endpoint='logout')
api.add_resource(RecipeIndex, '/recipes', endpoint='recipe_index')

if __name__ == '__main__':
    app.run(port=5555, debug=True)
