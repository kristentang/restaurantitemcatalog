from flask import Flask, render_template, request
from flask import redirect, url_for, flash, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Restaurant, Base, MenuItem, User
from flask import session as login_session
import random
import string  # create pseudorandom string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

# create an instance of the class,
# with name of the running application as argument
app = Flask(__name__)
engine = create_engine('sqlite:///restaurantmenuwithusers.db')
Base.metadata.bind = engine

# Declare client ID by referencing client secrets file
CLIENT_ID = json.loads(open('client_secrets.json', 'r')
                       .read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu Application"


# Create a state token to prevent request forgery
# Store it in the session for later validation
@app.route('/login')
def showLogin():
    state = ''.join(random
                    .choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    # login session object
    login_session['state'] = state
    # return "The current session state is %s" %login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    # Confirm that token that client sends to the server matches
    # the token the server sent to the client (round-trip verification)
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data
    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        # Exchanges authorization code for credentials object
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(json
                                 .dumps('Upgrade auth code fail.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Check that the access token is valid
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 50)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is for the intended user
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_resposne(json
                                 .dumps("Token's user ID doesn't "
                                        "match given user ID."), 401)
        response.header['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app
    if result['issued_to'] != CLIENT_ID:
        response = make_response(json
                                 .dumps("Token's client ID "
                                        "does not match app's"), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check to see if user is already logged in
    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json
                                 .dumps('Current user '
                                        'is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 100px; height: 100px;border-radius: '
    output += '150px;-webkit-border-radius: '
    output += '150px;-moz-border-radius: 150px;"> '
    return output


@app.route("/gdisconnect")
def gdisconnect():
    # Only disconnect a connected user, else 401 error
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(json.dumps('Current '
                                            'user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    # Execute HTTP GET request to revoke current token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result

    if result['status'] == '200':
        # Reset the user's session
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return redirect(url_for('allRestaurants'))

    else:
        # For whatever reason, the given token was Invalid
        response = make_response(json.dumps('Failed to revoke '
                                            'token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# API ENDPOINTS WITH JSON
@app.route('/restaurants/JSON')  # ROUTE
def restaurantsSON():
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    restaurants = session.query(Restaurant).all()
    # Use loop to serialize database entries
    return jsonify(
        Restaurants=[restaurant.serialize for restaurant in restaurants])


@app.route('/restaurants/<int:restaurant_id>/menu/JSON')  # ROUTE
def restaurantMenuJSON(restaurant_id):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id).all()
    # Use loop to serialize database entries
    return jsonify(MenuItems=[i.serialize for i in items])


@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/JSON')  # ROUTE
def menuItemJSON(restaurant_id, menu_id):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    menuItem = session.query(MenuItem).filter_by(id=menu_id).one()
    # Use loop to serialize database entries
    return jsonify(MenuItem=menuItem.serialize)


# ALL RESTAURANTS
@app.route('/')
@app.route('/restaurants')
@app.route('/restaurants/')
def allRestaurants():
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    restaurants = session.query(Restaurant).all()
    if 'username' in login_session:
        return render_template('allrestaurants.html', restaurants=restaurants,
                               username=login_session['username'],
                               picture=login_session['picture'],
                               user_id=login_session['user_id'])
    else:
        return render_template('allrestaurants.html', restaurants=restaurants)


# NEW RESTAURANT
# responds to get and post requests
@app.route('/restaurants/new', methods=['GET', 'POST'])
@app.route('/restaurants/new/', methods=['GET', 'POST'])
def newRestaurant():
    if 'username' not in login_session:
        return redirect('/login')
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    if request.method == 'POST':
        print login_session['username']
        newRestaurant = Restaurant(name=request.form['name'],
                                   user_id=login_session['user_id'])
        session.add(newRestaurant)
        session.commit()
        flash(newRestaurant.name + " has been created")
        return redirect(url_for('allRestaurants'))
    else:
        return render_template('newrestaurant.html',
                               username=login_session['username'],
                               picture=login_session['picture'])


# EDIT RESTAURANT
@app.route('/restaurants/<int:restaurant_id>/edit', methods=['GET', 'POST'])
@app.route('/restaurants/<int:restaurant_id>/edit/', methods=['GET', 'POST'])
def editRestaurant(restaurant_id):
    if 'username' not in login_session:
        return redirect('/login')
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    editedRestaurant = session.query(Restaurant).filter_by(
        id=restaurant_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedRestaurant.name = request.form['name']
        session.add(editedRestaurant)
        session.commit()
        flash(editedRestaurant.name + " has been edited")
        return redirect(url_for('allRestaurants'))
    else:
        return render_template(
            'editrestaurant.html', restaurant_id=restaurant_id,
            restaurant=editedRestaurant, username=login_session['username'],
            picture=login_session['picture'])


# DELETE RESTAURANT
@app.route('/restaurants/<int:restaurant_id>/delete', methods=['GET', 'POST'])
@app.route('/restaurants/<int:restaurant_id>/delete/', methods=['GET', 'POST'])
def deleteRestaurant(restaurant_id):
    if 'username' not in login_session:
        return redirect('/login')
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    restaurantToDelete = session.query(Restaurant).filter_by(
        id=restaurant_id).one()
    if request.method == 'POST':
        session.delete(restaurantToDelete)
        session.commit()
        flash(restaurantToDelete.name + " has been deleted")
        return redirect(url_for('allRestaurants'))
    else:
        return render_template(
            'deleterestaurant.html', restaurant_id=restaurant_id,
            restaurant=restaurantToDelete, username=login_session['username'],
            picture=login_session['picture'])


# RESTAURANT MENU
@app.route('/restaurants/<int:restaurant_id>/menu')
def restaurantMenu(restaurant_id):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id)
    if 'username' in login_session:
        return render_template('menu.html', restaurant=restaurant,
                               items=items, username=login_session['username'],
                               picture=login_session['picture'],
                               user_id=login_session['user_id'])
    else:
        return render_template('menu.html', restaurant=restaurant, items=items)


# NEW MENU ITEM
@app.route('/restaurants/<int:restaurant_id>/menu/new/',
           methods=['GET', 'POST'])
def newMenuItem(restaurant_id):
    if 'username' not in login_session:
        return redirect('/login')
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    newItem = MenuItem(restaurant_id=restaurant_id,
                       user_id=login_session['user_id'])
    if request.method == 'POST':
        if request.form['name']:
            newItem.name = request.form['name']
        if request.form['description']:
            newItem.description = request.form['description']
        if request.form['price']:
            newItem.price = request.form['price']
        session.add(newItem)
        session.commit()
        flash(newItem.name + " has been created")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        return render_template('newmenuitem.html', restaurant_id=restaurant_id,
                               username=login_session['username'],
                               picture=login_session['picture'])


# EDIT MENU ITEM
@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/edit/',
           methods=['GET', 'POST'])
def editMenuItem(restaurant_id, menu_id):
    if 'username' not in login_session:
        return redirect('/login')
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    editedItem = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        session.add(editedItem)
        session.commit()
        flash(editedItem.name + " has been edited")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        # USE THE RENDER_TEMPLATE FUNCTION BELOW TO SEE THE VARIABLES YOU
        # SHOULD USE IN YOUR EDITMENUITEM TEMPLATE
        # pass in three varaibles - item is item we want to edit
        return render_template(
            'editmenuitem.html', restaurant_id=restaurant_id,
            menu_id=menu_id, item=editedItem,
            username=login_session['username'],
            picture=login_session['picture'])


# DELETE MENU ITEM
@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/delete/',
           methods=['GET', 'POST'])
def deleteMenuItem(restaurant_id, menu_id):
    if 'username' not in login_session:
        return redirect('/login')
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    itemToDelete = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        # delete item and redirect back to main menu
        session.delete(itemToDelete)
        session.commit()
        flash(itemToDelete.name + " has been deleted")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        # render template for deleting menu item with item to delete
        return render_template(
            'deleteMenuItem.html', restaurant_id=restaurant_id,
            menu_id=menu_id, item=itemToDelete,
            username=login_session['username'],
            picture=login_session['picture'])


# Takes an email address and returns an ID number if the email is in the DB
def getUserID(email):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# If a user ID is passed in, it will return the user object
def getUserInfo(user_id):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    user = session.query(User).filter_by(id=user_id).one()
    return user


# Takes in a login_session as input and creates a new user in the db
def createUser(login_session):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


if __name__ == '__main__':
    # creates sessions, weak for dev purposes
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
