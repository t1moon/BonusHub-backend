# -*- coding: utf-8 -*-
import os

import MySQLdb
from flask import Blueprint, session, jsonify, request, send_from_directory, app
from flask_login import login_required, login_user, logout_user, current_user
from werkzeug.utils import secure_filename

from api.queries import INSERT_OPERATION_ADD, INSERT_OPERATION_WITHDRAW, SELECT_STATISTIC, SELECT_INFO, EDIT_HOST, \
    UPLOAD_PHOTO
from extentions import mysql
from models.host import Host
from models.user import User

UPLOAD_FOLDER = os.path.split(__file__)[0] + "/.." + "/static/img"

host_bp = Blueprint('host_bp', __name__)

barmen_counter = 1
barmens = list()
barmens.append(User('test_user', 'qwerty', barmen_counter))
barmen_counter = barmen_counter + 1

while barmen_counter < 10:
    barmens.append(User('test_user' + str(barmen_counter), 'qwerty' + str(barmen_counter), barmen_counter))
    barmen_counter = barmen_counter + 1

shops = list()

i = 0
while i < 10:
    shops.append(Host(id=i, title="shop" + str(i), description="Best cafe" + str(i),
                      address='Pushkina', time_open='9:00', time_close='23:00', logo='jhdun.jpg'))
    i = i + 1


def get_id(login, password):
    for barmen in barmens:
        if barmen.login == login and barmen.password == password:
            return barmen.id
    # conn = mysql.connect()
    # cursor = conn.cursor()
    # cursor.execute("SELECT host_id FROM host WHERE user_id = " + user_id)
    # host_id = cursor.fetchone()[0]
    # return host_id


@host_bp.route('register/', methods=['POST'])
def register():
    global barmen_counter
    data = dict((k, v) for (k, v) in request.json.items())
    login = data.get('login', None)
    password = data.get('password', None)
    if login != None and password != None:
        for barmen in barmens:
            if barmen.login == login:
                return jsonify({'code': 1, 'message': 'already registered'})
        barmens.append(User(login, password, barmen_counter))
        shops.append(Host())
        barmen_counter = barmen_counter + 1
        return jsonify({'code': 0, 'message': 'you are registered'})
    return jsonify({'code': 1, 'message': 'wrong login/password'})


@host_bp.route('login/', methods=['POST'])
def login():
    data = dict((k, v) for (k, v) in request.json.items())
    login = data.get('login', None)
    password = data.get('password', None)
    isHosted = False
    current_id = get_id(login, password)
    if shops[current_id].id != 0:
        isHosted = True
    if current_id != 0:
        if 'username' in session:
            if current_user and session['username'] == login:
                session.pop('username', None)
                logout_user()
                user = User(login, password)
                login_user(user)
                session['id'] = login
                return jsonify({'code': 0, 'message': 'You are already logged in', 'isHosted': isHosted})
            else:
                session.pop('username', None)
                logout_user()
                return jsonify({'code': 1, 'message': 'You are already logged in as another', 'isHosted': False})
        user = User(login, password)
        login_user(user)
        session['username'] = login
        return jsonify({'code': 0, 'message': 'Logged in', 'isHosted': isHosted})
    return jsonify({'code': 1, 'message': 'Wrong credentials', 'isHosted': False})


@host_bp.route('logout/', methods=['POST'])
@login_required
def logout():
    session.pop('username', None)
    logout_user()
    return jsonify({'code': 0})


@host_bp.route('edithost/', methods=['POST'])
@login_required
def edit_host():
    data = dict((k, v) for (k, v) in request.json.items())
    current_id = data.get('id', None)
    password = data.get('password', None)
    return jsonify({'code': 0})


@host_bp.route('<host_id>/get_client/<identificator>/', methods=['GET'])
def get_client(host_id, identificator):
    print host_id, identificator
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM client_host WHERE host_id = " + host_id + " AND client_id = \
                        (SELECT client_id FROM client WHERE identificator = '" + identificator + "')")
    points = cursor.fetchone()[0]
    print points
    response = {'code': 0, 'points': points}
    conn.close()
    return jsonify(response)


@host_bp.route('<host_id>/statistic/', methods=['GET'])
def get_statistic(host_id):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute(SELECT_STATISTIC, [host_id])
    operations = cursor.fetchall()
    response = []
    for i in operations:
        response.append({"date": i[0], "avg_bill": i[1], "income": i[2], "outcome": i[3]})
    conn.close()
    return jsonify({"code": 0, "response": response})


@host_bp.route('<host_id>/info/', methods=['GET'])
def get_info(host_id):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute(SELECT_INFO, [host_id])
    host = cursor.fetchone()
    response = {"title": host[0], "description": host[1], "address": host[2], "time_open": host[3],
                "time_close": host[4], "profile_image": host[5]}
    conn.close()
    return jsonify(response)


@host_bp.route('edit_host/', methods=['POST'])
def edit_host_info():
    data = dict((k, v) for (k, v) in request.json.items())
    host_id = str(data.get('host_id', None))
    host = data.get('host', None)
    title = host['title']
    description = host['description']
    address = host['address']
    time_open = host['time_open']
    time_close = host['time_close']

    conn = mysql.connect()
    cursor = conn.cursor()

    try:
        cursor.execute(EDIT_HOST, [title,description,address,time_open,time_close, host_id])
        conn.commit()
        if (conn.affected_rows() > 0):
            response = {'code': 0, 'message': 'Данные о заведении успешно изменены'}
        else:
            response = {'code': 1, 'message': 'Данные не изменились'}
        conn.close()

    except (MySQLdb.Error, MySQLdb.Warning):
        conn.close()
        response = {'code': 2, 'message': 'Неизвестная ошибка'}

    return jsonify(response)


@host_bp.route('update_points/', methods=['POST'])
def update_points():
    data = dict((k, v) for (k, v) in request.json.items())

    host_id = str(data.get('host_id', None))
    bill = data.get('bill', None)
    is_add = data.get('is_add', None)
    client_identificator = data.get('client_identificator', None)

    conn = mysql.connect()
    cursor = conn.cursor()

    if is_add:
        cursor.execute("SELECT add_percent FROM host WHERE host_id = " + host_id)
        add_percent = float(cursor.fetchone()[0]) / 100
        add_points = str(int(bill * add_percent))
        cursor.execute("UPDATE client_host SET points = points + " + add_points + " WHERE host_id = " + host_id + " AND client_id = \
                                (SELECT client_id FROM client WHERE identificator = '" + client_identificator + "')")
        cursor.execute(INSERT_OPERATION_ADD, [host_id, add_points, bill, client_identificator])

        response = {'code': 0, 'message': 'Бонусы были успешно зачислены'}
    else:
        cursor.execute("SELECT points FROM client_host WHERE host_id = " + host_id + " AND client_id = \
                                (SELECT client_id FROM client WHERE identificator = '" + client_identificator + "')")
        points = int(cursor.fetchone()[0])
        if points >= bill:
            points = str(points - bill)
            cursor.execute(
                "UPDATE client_host SET points = " + points + " WHERE host_id = " + host_id + " AND client_id = \
                                            (SELECT client_id FROM client WHERE identificator = '" + client_identificator + "')")
            cursor.execute(INSERT_OPERATION_WITHDRAW, [host_id, bill, bill, client_identificator])

            response = {'code': 0, 'message': 'Бонусы были успешно списаны'}
        else:
            response = {'code': 0, 'message': 'Извините, но бонусов не хватает'}
    conn.commit()
    conn.close()
    return jsonify(response)


@host_bp.route('testsession/', methods=['GET'])
@login_required
def test_session():
    return jsonify({'code': 0, 'message': 'wonderful!'})


@host_bp.route('media/<filename>', methods=['GET'])
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@host_bp.route('<host_id>/upload/', methods=['POST'])
def upload(host_id):
    file = request.files.get("picture")
    filename = secure_filename(file.filename)
    file.save(UPLOAD_FOLDER + "/" + filename)
    conn = mysql.connect()
    cursor = conn.cursor()
    try:
        cursor.execute(UPLOAD_PHOTO, [filename, host_id])
        conn.commit()
        response = {'code': 0, 'message': 'Картинка успешно загружена'}
    except (MySQLdb.Error, MySQLdb.Warning):
        response = {'code': 2, 'message': 'Неизвестная ошибка'}
    conn.close()
    return jsonify(response)
