#2013-03-19 create user

create user 'bu' identified by 'bupassword@';
grant all privileges on backend.* to 'bu' with grant option;