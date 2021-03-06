# Application modules
from flask import Flask, jsonify, request
from flaskext.mysql import MySQL
from marshmallow import ValidationError
from flask_bcrypt import Bcrypt
import jwt

# General modules
from functools import wraps
from datetime import datetime, timedelta, date

# Custom modules
from db import MySQLConnection
from random_password_generator import random_password_generator
from schema import AddUser, UserLogin, PasswordChange, EditUser
from util import get_items, generate_placeholders, get_update_items, get_table_name

# creating an instance of Flask class
app = Flask(__name__)

app.config.from_pyfile('config.py')
mysql = MySQL()
mysql.init_app(app)
bcrypt = Bcrypt(app)

# For random password generation on account creation
generate_password = random_password_generator()


def auth_wrapper(method):
	@wraps(method)
	def wrapper(*args, **kwargs):
		access_token = request.headers.get('jwt-auth-token')
		try:
			payload = jwt.decode(access_token.encode('utf-8'), app.config['TOKEN_KEY'], algorithms='HS256')
			username = payload['username']
			current_user = None
			user_type = None

			with MySQLConnection(mysql) as connection:
				with connection.cursor() as cur:
					get_user = "SELECT username, id, user_type FROM EmployeeLogin WHERE username = %s"
					cur.execute(get_user, username)
					result = cur.fetchall()

					if not result:
						raise Exception('Invalid Token')

					fetched_username, current_user, user_type = result[0]

			return method(current_user_id=current_user, current_user_type=user_type, *args, **kwargs)
			
		except jwt.exceptions.ExpiredSignatureError as e:
			return jsonify({ 'message': 'Session Expired' }), 403

		except Exception as e:
			print('Error:', e)
			return jsonify({ 'message': 'Forbidden' }), 403

	return wrapper


@app.route('/api/login', methods=['POST'])
def login():
	try:
		data = UserLogin().load(request.get_json(force = True))
		username, password = data['username'], data['password']

		with MySQLConnection(mysql) as connection:
			with connection.cursor() as cur:
				get_password = "SELECT password FROM EmployeeLogin WHERE username = %s"
				cur.execute(get_password, username)
				result = cur.fetchall()

				if not result:
					raise Exception('Invalid Credentials')
				
				password_hash = result[0][0]

				if not password_hash or not bcrypt.check_password_hash(password_hash, password):
					raise Exception('Invalid Credentials')

		payload = { 'username': username, 'exp': datetime.utcnow() + timedelta(minutes=30) }
		token = jwt.encode(payload, app.config['TOKEN_KEY'], algorithm='HS256')

		return jsonify({ 'access_token': token.decode('utf-8') })

	except Exception as e:
		if str(e) == 'Invalid Credentials':
			return jsonify({ 'message': str(e) }), 401
		print('Error:', e)
		return jsonify({ 'message': 'Unexpected Error Occured' }), 500


@app.route('/api/users', methods=['GET'])
def get_users():
	try:
		from_record = 0 if request.args.get('from') is None else int(request.args.get('from'))
		limit = 50 if request.args.get('limit') is None else int(request.args.get('limit'))
		if limit > 100 or limit <= 0 or from_record < 0:
			raise Exception('Unprocessable Entity')
		
		with MySQLConnection(mysql) as connection:
			with connection.cursor() as cur:
				fetch_users = "SELECT first_name, last_name, title FROM EmployeeDetails LIMIT %s OFFSET %s"
				cur.execute(fetch_users, (limit, from_record))
				result = cur.fetchall()

				users = []
				for user in result:
					fname, lname, title = user
					users.append({ 'first_name': fname, 'last_name': lname, 'title': title })
		
		return jsonify({ 'data': users })
	
	except Exception as e:
		if str(e) == 'Unprocessable Entity':
			return jsonify({ 'message': str(e) }), 422
		print('Error: ', e)
		return jsonify({ 'message': 'Unexpected Error Occured' }), 500


@app.route('/api/user/<user_id>', methods=['GET'])
@auth_wrapper
def get_user(current_user_id, user_id, **kwargs):
	try:
		data = {}
		if int(user_id) == current_user_id:
			with MySQLConnection(mysql) as connection:
				with connection.cursor() as cur:
					fetch_users = "SELECT d.first_name, d.last_name, d.title, d.phone_number, d.date_of_birth, d.email, d.creation_time, d.modification_time, l.username, l.user_type FROM (SELECT * FROM EmployeeDetails WHERE id = %s) AS d INNER JOIN EmployeeLogin AS l ON d.id=l.id"
					cur.execute(fetch_users, user_id)
					
					user = cur.fetchall()[0]
					data = {
						'first_name': user[0],
						'last_name': user[1],
						'title': user[2],
						'phone_number': user[3],
						'date_of_birth': user[4],
						'email': user[5],
						'creation_time': user[6],
						'modification_time': user[7],
						'username': user[8],
						'user_type': user[9],
					}

		else:
			with MySQLConnection(mysql) as connection:
				with connection.cursor() as cur:
					fetch_users = "SELECT d.first_name, d.last_name, d.title, d.email, l.user_type FROM (SELECT * FROM EmployeeDetails WHERE id = %s) AS d INNER JOIN EmployeeLogin AS l ON d.id=l.id"
					cur.execute(fetch_users, user_id)
					
					user = cur.fetchall()[0]
					data = {
						'first_name': user[0],
						'last_name': user[1],
						'title': user[2],
						'email': user[3],
						'user_type': user[4]
					}
		
		return jsonify({ 'data': data })
	
	except Exception as e:
		print('Error: ', e)
		return jsonify({ 'message': 'Unexpected Error Occured' }), 500


@app.route('/api/pwd/<user_id>', methods=['PATCH'])
@auth_wrapper
def password_change(current_user_id, user_id, **kwargs):
	connection = None
	try:
		if current_user_id != int(user_id):
			raise Exception('Unauthorized')
		
		data = PasswordChange().load(request.get_json(force = True))
		old_password, new_password = data['old_password'], data['new_password']

		connection = mysql.connect()
		
		with connection.cursor() as cur:
			get_password = "SELECT password FROM EmployeeLogin WHERE id=%s"
			cur.execute(get_password, user_id)
			password_hash = cur.fetchall()[0][0]

			if not password_hash or not bcrypt.check_password_hash(password_hash, old_password):
				raise Exception('Invalid Credentials')
			
			pw_hash = bcrypt.generate_password_hash(new_password)
			login_query = "UPDATE EmployeeLogin SET password = %s WHERE id = %s"
			cur.execute(login_query, (pw_hash, user_id))

		connection.commit()
		return { 'message': 'Password Changed' }

	except ValidationError as err:
		return jsonify({ 'message': err.messages }), 400

	except Exception as e:
		if connection:
			connection.rollback()
		if str(e) == 'Unauthorized':
			return jsonify({ 'message': str(e) }), 401
		elif str(e) == 'Invalid Credentials':
			return jsonify({ 'message': str(e) }), 403
		print('Error: ', e)
		return jsonify({ 'message': 'Unexpected Error Occured' }), 500

	finally:
		if connection:
			connection.close()


@app.route('/api/add', methods=['POST'])
@auth_wrapper
def add_user(current_user_id, current_user_type):
	connection = None
	try:
		if current_user_type != 'admin':
			raise Exception('Unauthorized')
		
		data = AddUser().load(request.get_json(force = True))

		username, email, user_type = data['username'], data['email'], data['user_type']
		del data['username']
		del data['user_type']

		if data.get('options', None):
			options = data['options']
			del data['options']
		else:
			options = {}
		
		connection = mysql.connect()

		if user_type == 'manager':
			reporting_to = options['reporting_to']
			if reporting_to:
				with connection.cursor() as cur:
					admin_query = "SELECT id FROM AdminInfo WHERE id = %s"
					cur.execute(admin_query, reporting_to)

					admin_id = cur.fetchall()

					if not admin_id:
						raise Exception('Reporting to: Not an Admin')

		if user_type == 'staff':
			reporting_to = options['reporting_to']
			if reporting_to:
				with connection.cursor() as cur:
					manager_query = "SELECT id FROM ManagerInfo WHERE id = %s"
					cur.execute(manager_query, reporting_to)

					manager_id = cur.fetchall()

					if not manager_id:
						raise Exception('Reporting to: Not a Manager')

		keys, values = get_items(data)

		with connection.cursor() as cur:
			if options.get('is_primary', None):
				# dont insert another primary user if one is already present
				primary_users = "SELECT count(id) FROM AdminInfo where is_primary=true"
				cur.execute(primary_users)
				primary_user_count = cur.fetchall()[0][0]
				if primary_user_count:
					raise Exception('Primary user already exists')

			detail_query = "INSERT INTO EmployeeDetails ("+keys+") VALUES ("+generate_placeholders(len(values))+")"
			cur.execute(detail_query, values)

			cur.execute("SELECT id FROM EmployeeDetails WHERE email=%s", (email))
			user_id = cur.fetchall()[0][0]
			password = generate_password()
			print(password)
			pw_hash = bcrypt.generate_password_hash(password)
			login_query = "INSERT INTO EmployeeLogin VALUES ("+generate_placeholders(4)+")"
			cur.execute(login_query, (user_id, username, pw_hash, user_type))

			if user_type == 'admin':
				options['id'] = user_id
				keys, values = get_items(options)

				role_query = "INSERT INTO AdminInfo ("+keys+") VALUES ("+generate_placeholders(len(values))+")"
				cur.execute(role_query, values)	

			elif user_type == 'manager':
				options['id'] = user_id
				options['added_by'] = current_user_id
				keys, values = get_items(options)

				role_query = "INSERT INTO ManagerInfo ("+keys+") VALUES ("+generate_placeholders(len(values))+")"
				cur.execute(role_query, values)	

			elif user_type == 'staff':
				options['id'] = user_id
				options['added_by'] = current_user_id
				keys, values = get_items(options)

				role_query = "INSERT INTO StaffInfo ("+keys+") VALUES ("+generate_placeholders(len(values))+")"
				cur.execute(role_query, values)	

		connection.commit()
		return jsonify({ 'message': 'User Created' }), 201

	except ValidationError as err:
		return jsonify({ 'message': err.messages }), 400

	except Exception as err:
		if connection:
			connection.rollback()
		if str(err) == 'Primary user already exists' or str(err) == 'Reporting to: Not an Admin' or str(err) == 'Reporting to: Not a Manager':
			return jsonify({ 'message': str(err) }), 400
		elif str(err) == 'Unauthorized':
			return jsonify({ 'message': str(err) }), 401
		print("Unexpected error:", err)
		return jsonify({ 'message': 'Cannot process request' }), 500
		
	finally:
		if connection:
			connection.close()


@app.route('/api/user/<user_id>', methods=['PATCH'])
@auth_wrapper
def edit_user(user_id, current_user_id, current_user_type):
	try:
		with MySQLConnection(mysql) as connection:
			with connection.cursor() as cur:
				check_user = "SELECT user_type FROM EmployeeLogin WHERE id=%s"
				cur.execute(check_user, user_id)
				result = cur.fetchall()

				if not result:
					raise Exception('Not Found')

				old_user_type = result[0][0]

		data = EditUser().load(request.get_json(force = True))

		if data['change_type'] == 'detail':
			if not (current_user_id == int(user_id) or current_user_type == 'admin'):
				raise Exception('Unauthorized')
			
			detail = data['detail']

			with MySQLConnection(mysql) as connection:
				with connection.cursor() as cur:
					update_query = f"UPDATE EmployeeDetails SET {get_update_items(detail)} WHERE id = %s"
					cur.execute(update_query, user_id)
				connection.commit()

		elif data['change_type'] == 'scope':
			if current_user_type != 'admin':
				raise Exception('Unauthorized')

			new_user_type = data['scope']['to']

			if new_user_type == old_user_type:
				return jsonify({ 'message': 'No modification needed' }), 304

			with MySQLConnection(mysql) as connection:
				with connection.cursor() as cur:
					find_user = f"SELECT * FROM {get_table_name(old_user_type)} WHERE id = %s"
					cur.execute(find_user, user_id)
					result = cur.fetchall()[0][:-1]
					keys = ['id', 'added_by']
					if data['scope'].get('reporting_to', None):
						keys.append('reporting_to')
						result += (data['scope']['reporting_to'] ,)

					insert_user = f"INSERT INTO {get_table_name(new_user_type)} ({', '.join(keys)}) VALUES ({generate_placeholders(len(result))})"
					cur.execute(insert_user, result)

					update_user = f"UPDATE EmployeeLogin SET user_type = %s WHERE id = %s"
					cur.execute(update_user, (new_user_type, user_id))

					delete_user = f"DELETE FROM {get_table_name(old_user_type)} WHERE id = %s"
					cur.execute(delete_user, user_id)

				connection.commit()

		return jsonify({ 'message': 'User Edited' })

	except ValidationError as err:
		return jsonify({ 'message': err.messages }), 400

	except Exception as err:
		if str(err) == 'Unauthorized':
			return jsonify({ 'message': str(err) }), 401
		if str(err) == 'Not Found':
			return jsonify({ 'message': str(err) }), 404
		print("Unexpected error:", err)
		return jsonify({ 'message': 'Cannot process request' }), 500


@app.route('/api/user/<user_id>', methods=['DELETE'])
@auth_wrapper
def delete_user(user_id, current_user_type, **kwargs):
	try:
		if current_user_type != 'admin':
			raise Exception('Unauthorized')

		with MySQLConnection(mysql) as connection:
			with connection.cursor() as cur:
				check_user = "SELECT user_type FROM EmployeeLogin WHERE id=%s"
				cur.execute(check_user, user_id)
				result = cur.fetchall()

				if not result:
					raise Exception('Not Found')

				user_type = result[0][0]

		if user_type == 'admin':
			with MySQLConnection(mysql) as connection:
				with connection.cursor() as cur:
					primary_user = "SELECT is_primary FROM AdminInfo WHERE id = %s"
					cur.execute(primary_user, user_id)
					result = cur.fetchall()[0][0]

					if result:
						raise Exception('Primary user can\'t be deleted')

					change_reporting_to = "UPDATE ManagerInfo SET reporting_to = NULL WHERE reporting_to = %s"
					cur.execute(change_reporting_to, user_id)

					remove_info = "DELETE FROM AdminInfo WHERE id = %s"
					cur.execute(remove_info, user_id)

					remove_login = "DELETE FROM EmployeeLogin WHERE id = %s"
					cur.execute(remove_login, user_id)

					remove_details = "DELETE FROM EmployeeDetails WHERE id = %s"
					cur.execute(remove_details, user_id)

				connection.commit()

		elif user_type == 'manager':
			with MySQLConnection(mysql) as connection:
				with connection.cursor() as cur:
					change_reporting_to = "UPDATE StaffInfo SET reporting_to = NULL WHERE reporting_to = %s"
					cur.execute(change_reporting_to, user_id)

					remove_info = "DELETE FROM ManagerInfo WHERE id = %s"
					cur.execute(remove_info, user_id)

					remove_login = "DELETE FROM EmployeeLogin WHERE id = %s"
					cur.execute(remove_login, user_id)

					remove_details = "DELETE FROM EmployeeDetails WHERE id = %s"
					cur.execute(remove_details, user_id)
				
				connection.commit()

		elif user_type == 'staff':
			with MySQLConnection(mysql) as connection:
				with connection.cursor() as cur:
					remove_info = "DELETE FROM StaffInfo WHERE id = %s"
					cur.execute(remove_info, user_id)

					remove_login = "DELETE FROM EmployeeLogin WHERE id = %s"
					cur.execute(remove_login, user_id)

					remove_details = "DELETE FROM EmployeeDetails WHERE id = %s"
					cur.execute(remove_details, user_id)

				connection.commit()

		return jsonify({ 'message': 'User Deleted' })

	except Exception as err:
		if str(err) == 'Unauthorized':
			return jsonify({ 'message': str(err) }), 401
		if str(err) == 'Primary user can\'t be deleted':
			return jsonify({ 'message': str(err) }), 403
		if str(err) == 'Not Found':
			return jsonify({ 'message': str(err) }), 404
		print("Unexpected error:", err)
		return jsonify({ 'message': 'Cannot process request' }), 500


@app.route('/', methods=['GET'])
def home():
	return 'Hello There!'

if __name__ == '__main__':
	app.run()
