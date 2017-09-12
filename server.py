from flask import Flask, render_template, request, redirect, session, flash
import re
import md5
import os, binascii
salt = binascii.b2a_hex(os.urandom(15))
from mysqlconnection import MySQLConnector

app = Flask(__name__)
app.secret_key = 'secret'
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')

mysql = MySQLConnector(app,'login_reg_db')

@app.route('/')
def index():
    if 'user' not in session:
        return render_template('login.html')
    else:
        return render_template('index.html')

@app.route('/home', methods=['GET','POST'])
def home():
    return redirect('/')

@app.route('/login', methods=['POST'])
def login():
    query = "SELECT * FROM users WHERE email = :email"

    data = {
            'email': request.form['email']
            }

    match = mysql.query_db(query, data)

    if len(match) > 0:
        encrypted_password = md5.new(request.form['password'] + match[0]['salt']).hexdigest()

        if match[0]['password'] == encrypted_password:
            session['user'] = {
                                'id': match[0]['id'],
                                'fname': match[0]['fname'],
                                'lname': match[0]['lname'],
                                'email': match[0]['email']
                                }
            return redirect('/')
        else:
            flash('Invalid password!')
            return redirect('/')
    else:
        return redirect('/register')

@app.route('/register')
def reg():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    error = False

    if len(request.form['fname']) < 2 and request.form['fname'].isalpha()==False:
        error = True
        flash('First name needs to be at least 2 characters and include letters only')

    if len(request.form['lname']) < 2 and request.form['lname'].isalpha()==False:
        error = True
        flash('Last name needs to be at least 2 characters and include letters only')

    if not EMAIL_REGEX.match(request.form['email']):
        error = True
        flash('Enter a valid email')

    if len(request.form['password']) in range(0,9):
        error = True
        flash('Password needs to be at least 8 characters')

    if request.form['password'] != request.form['confirm']:
        error = True
        flash('Passwords do not match')

    if error == False:
        salt = binascii.b2a_hex(os.urandom(15))
        hashed_pw = md5.new(request.form['password'] + salt).hexdigest()

        query = "INSERT INTO users (fname, lname, email, password, salt, created_at, updated_at) VALUES (:fname, :lname, :email, :hashed_pw, :salt, NOW(), NOW())"

        data = {
                'fname': request.form['fname'],
                'lname': request.form['lname'],
                'email': request.form['email'],
                'hashed_pw': hashed_pw,
                'salt': salt
                }

        user = mysql.query_db(query, data)

        session['user'] = {
                            'fname': request.form['fname'],
                            'lname': request.form['lname'],
                            'email': request.form['email']
                            }

        return redirect('/')
    else:
        return redirect('/register')

@app.route('/friends')
def friends():
    query = "SELECT users.id, CONCAT(user2.fname,' ',user2.lname) as name, user2.email as email, DATE_FORMAT(friendships.created_at, '%M %e, %Y') as friends_since FROM users LEFT JOIN friendships ON users.id = friendships.user_id LEFT JOIN users as user2 ON user2.id = friendships.friend_id WHERE users.id = :user_id"

    data = {
            'user_id': session['user']['id']
            }

    friends = mysql.query_db(query, data)

    return render_template('friends.html', friends = friends)

@app.route('/addfriend', methods=['POST'])
def addfriend():
    if request.form['email'] == session['user']['email']:
        flash('Cannot add self as friend')
        return redirect('/friends')

    query = "SELECT users.id, users.fname, CONCAT(user2.fname,' ',user2.lname) as name, user2.email as email FROM users LEFT JOIN friendships ON users.id = friendships.user_id LEFT JOIN users as user2 ON user2.id = friendships.friend_id WHERE users.id = :user_id AND user2.email = :email"

    data = {
            'user_id': session['user']['id'],
            'email': request.form['email']
            }

    repeat = mysql.query_db(query, data)

    if len(repeat) > 0:
        flash('Already a friend!')
        return redirect('/friends')

    query = "SELECT * FROM users WHERE email = :email"

    data = {
            'email': request.form['email']
            }

    friend = mysql.query_db(query, data)

    if len(friend) > 0:
        query = "INSERT INTO friendships(user_id, friend_id, created_at, updated_at) VALUES (:user_id, :friend_id, NOW(), NOW())"

        data = {
                'user_id': session['user']['id'],
                'friend_id': friend[0]['id'],
        }

        addfriend = mysql.query_db(query, data)

    else:
        flash('Friend not found')

    return redirect('/friends')

@app.route('/message', methods=['POST'])
def message():
    query = "INSERT INTO messages (content, created_at, updated_at, user_id) VALUES (:content, NOW(), NOW(), :user_id)"

    data = {
            'content': request.form['message'],
            'user_id': session['user']['id']
            }

    message = mysql.query_db(query, data)

    return redirect('/wall')

@app.route('/comment', methods=['POST'])
def comment():
    query = "INSERT INTO comments (content, created_at, updated_at, message_id, user_id) VALUES (:content, NOW(), NOW(), :message_id, :user_id)"

    data = {
            'content': request.form['comment'],
            'message_id': request.form['msgid'],
            'user_id': session['user']['id']
            }

    comment = mysql.query_db(query, data)

    return redirect('/wall')

@app.route('/wall')
def wall():
    query = "SELECT messages.id, messages.content as messages_content, DATE_FORMAT(messages.created_at, '%M %e, %Y at %h: %m %p') as time, DATE_FORMAT(messages.created_at, '%h: %m') as timer, CONCAT(users.fname,' ',users.lname) as name, comments.message_id as comment_id, comments.content as comment, DATE_FORMAT(comments.created_at, '%M %e, %Y at %h: %m %p') as comment_time, CONCAT(user2.fname,' ',user2.lname) as commenter_name FROM messages JOIN users ON messages.user_id = users.id LEFT JOIN comments ON comments.message_id = messages.id JOIN users as user2 ON comments.user_id = user2.id ORDER BY messages.id DESC"

    # messages = mysql.query_db("SELECT * FROM messages")
    #
    # for message in messages:
    #     message['comments'] = mysql.query_db("SELECT * FROM comments WHERE message_id = :m_id", {'m_id': message['id']})

    posts = mysql.query_db(query)

    box = {}

    for post in posts:
        if post['id'] in box:
            box[post['id']]['comments'].append({'comment': post['comment'], 'comment_time': post['comment_time'], 'commenter_name': post['commenter_name']})
        else:
            box[post['id']] = post
            box[post['id']]['comments'] = []
            box[post['id']]['comments'].append({'comment': post['comment'], 'comment_time': post['comment_time'], 'commenter_name': post['commenter_name']})

    for post in box.values():
        for comment in post['comments']:
            print comment

    return render_template('wall.html', posts = posts, box=box)

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user')
    return redirect('/')

app.run(debug=True)
