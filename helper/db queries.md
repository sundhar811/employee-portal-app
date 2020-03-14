### Create database:
```
CREATE DATABASE flask;
```
### Create Employee Details Table:
```
CREATE TABLE EmployeeDetails (id INT UNSIGNED AUTO_INCREMENT NOT NULL, first_name VARCHAR(20), last_name VARCHAR(20) NOT NULL, title VARCHAR(30) NOT NULL, phone_number VARCHAR(15), date_of_birth DATE NOT NULL, email VARCHAR(255) NOT NULL, PRIMARY KEY (id));
```
### Create Employee Login Table:
```
CREATE TABLE EmployeeLogin (id INT UNSIGNED NOT NULL, username VARCHAR(20), password BINARY(60) NOT NULL, PRIMARY KEY (username), FOREIGN KEY (id) REFERENCES EmployeeDetails (id));
```
### Create Admin Info Table:
```
CREATE TABLE AdminInfo (id INT UNSIGNED, is_super BOOL DEFAULT false, is_primary BOOL DEFAULT false, FOREIGN KEY (id) REFERENCES EmployeeDetails (id));
```
### Create Manager Info Table:
```
CREATE TABLE ManagerInfo (id INT UNSIGNED, added_by INT UNSIGNED, reporting_to INT UNSIGNED, FOREIGN KEY (id) REFERENCES EmployeeDetails (id), FOREIGN KEY(added_by) REFERENCES AdminInfo (id), FOREIGN KEY (reporting_to) REFERENCES AdminInfo (id));
```
### Create Staff Info Table:
```
CREATE TABLE StaffInfo (id INT UNSIGNED, added_by INT UNSIGNED, reporting_to INT UNSIGNED, FOREIGN KEY (id) REFERENCES EmployeeDetails (id), FOREIGN KEY(added_by) REFERENCES AdminInfo (id), FOREIGN KEY (reporting_to) REFERENCES ManagerInfo (id));
```