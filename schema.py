from marshmallow import Schema, fields, validate

class UserOptions(Schema):
  is_super = fields.Boolean()
  is_primary = fields.Boolean()
  reporting_to = fields.Integer()

class AddUser(Schema):
  user_type = fields.String(validate=validate.OneOf(["admin", "manager", "staff"]))
  first_name = fields.String(validate=validate.Length(max=20))
  last_name = fields.String(required = True, validate=validate.Length(max=20))
  title = fields.String(required = True, validate=validate.Length(max=30))
  phone_number = fields.String(validate=validate.Length(max=15))
  date_of_birth = fields.Date(required = True) # ISO Format: YYYY-MM-DD
  email = fields.Email(required = True)
  username = fields.String(required = True, validate=validate.Length(max=20))
  options = fields.Nested(UserOptions)

class UserLogin(Schema):
  username = fields.String(required = True)
  password = fields.String(required = True)

class PasswordChange(Schema):
  old_password = fields.String(required = True)
  new_password = fields.String(required = True)

class DetailChange(Schema):
  first_name = fields.String(validate=validate.Length(max=20))
  last_name = fields.String(validate=validate.Length(max=20))
  title = fields.String(validate=validate.Length(max=30))
  phone_number = fields.String(validate=validate.Length(max=15))
  date_of_birth = fields.Date() # ISO Format: YYYY-MM-DD
  email = fields.Email()

class ScopeChange(Schema):
  to = fields.String(required = True, validate=validate.OneOf(["manager", "staff"]))
  reporting_to = fields.Integer()

class EditUser(Schema):
  change_type = fields.String(required = True, validate=validate.OneOf(['detail', 'scope']))
  detail = fields.Nested(DetailChange)
  scope =fields.Nested(ScopeChange)
