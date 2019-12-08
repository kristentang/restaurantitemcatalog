# Project: Item Catalog

Logs Analysis is an internal reporting tool that uses information from a newspaper database to analyze the preferences of the site's readers. It is a project for Udacity's Full Stack Developer Nanodegree.
Item catalog is an application that provides a list of dishes within a list of menus and provides a user registration and authentication system. Menus and items can be viewed, and registered users can post, edit and delete their own items.
## Requirements

1. Install [VirtualBox](https://www.virtualbox.org/wiki/Download_Old_Builds_5_1)
2. Install [Vagrant](https://www.vagrantup.com/downloads.html)
3. Download the VM configuration by downloading or forking and cloning this repository: [https://github.com/udacity/fullstack-nanodegree-vm](https://github.com/udacity/fullstack-nanodegree-vm)

## Instructions

1. From your terminal inside the vagrant subdirectory, run the command vagrant up.
```
cd Desktop/Nanodegree/fullstack-nanodegree-vm/vagrant
```
```
vagrant up
```

2. Run the command vagrant ssh
```
vagrant ssh
```

3. In Vagrant, navigate to shared directory
```
cd /vagrant
```

4. Download or clone this repository and navigate to it
```
cd restaurants
```

5. Set up the database
```
python database_setup.py
```

6. Insert some starter values
```
python lotsofmenus.py
```

7. Run the application
```
python finalproject.py
```
8. Open [http://localhost:5000/](http://localhost:5000/) in your browser

## Project Features ##
1. This project implements JSON endpoints
    - [/restaurants/JSON](http://localhost:5000/restaurants/JSON): Returns JSON of restaurants
    - [/restaurants/restaurant_id/menu/JSON](http://localhost:5000/restaurants/1/menu/JSON):
    Returns JSON of menu for a specific menu item
    - [/restaurants/restaurant_id/menu/menu_id/JSON](http://localhost:5000/restaurants/1/menu/1/JSON): Returns JSON of menu for a specific menu item


2. This project implements CRUD features:
    - Create: Users can create new items
    - Read: Category and item information is read from a database
    - Update: Users can update currently existing items
    - Delete: Users can delete currently existing items


3. OAuth Authentication and Authorization
