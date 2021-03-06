# -*- coding: utf-8 -*-
"""
    Barbican
    ~~~~~~~~

    A proof of concept implementation of a key management server for
    use with the postern agent (https://github.com/cloudkeep/postern).

    DO NOT USE THIS IN PRODUCTION. IT IS NOT SECURE IN ANY WAY.
    YOU HAVE BEEN WARNED.

    :copyright: (c) 2013 by Jarret Raim
    :license: Apache 2.0, see LICENSE for details
"""
import os
from flask import Flask, render_template, redirect, flash, request
from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqlamodel import ModelView
from flask.ext import login, wtf
from flask.ext.login import login_user
from barbican_api import api
from database import db_session, init_db
from models import User, Tenant, Key, Policy, Event, Agent, Tag
import re

app = Flask(__name__)
app.secret_key = '79f9823f1f0---DEVELOPMENT---c46cebdd1c8f3d0742e02'
app.register_blueprint(api)

admin = Admin(app, name="Barbican Admin")
admin.add_view(ModelView(User, db_session))
admin.add_view(ModelView(Tenant, db_session))
admin.add_view(ModelView(Key, db_session))
admin.add_view(ModelView(Policy, db_session))
admin.add_view(ModelView(Event, db_session))
admin.add_view(ModelView(Agent, db_session))
admin.add_view(ModelView(Tag, db_session))

login_manager = login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@app.route("/")
@login.login_required
def hello():
    return render_template("index.html")


@app.route("/events")
@login.login_required
def events():
    return render_template("events.html")


@app.route("/agents", methods=["GET", "POST"])
@login.login_required
def agents():
    if request.method == 'POST':
        # need to update all agents since it is possible to disable pairing for them all
        all_data = request.form
        length = int(all_data["example_length"])
        ids = []
        for k in all_data:
            m = re.match('check(\d+)', k)
            if m is not None:
                id = m.group(1)
                ids.append(int(id))
        min_id = min(ids) / length * length + 1
        id_range = range(min_id, min_id + length)
        agents = Agent.query.order_by(Agent.id)
        for agent in agents.all():
            if agent.id not in id_range:
            # this is needed because POST from the datatable only contains current page
            # We only change the agent that falls within this range. 
                continue
            if agent.id in ids:
                agent.paired = True
            else:
                agent.paired = False
                db_session.commit()
        
        return render_template("agents.html")
    else:
        return render_template("agents.html")


#
#   Login forms
#
class LoginForm(wtf.Form):
    login = wtf.TextField(validators=[wtf.required()])
    password = wtf.PasswordField(validators=[wtf.required()])

    def validate_login(self, field):
        user = self.get_user()
        if user is None or user.password != self.password.data:
            raise wtf.ValidationError('Invalid username or credentials.')

    def get_user(self):
        return User.query.filter_by(name=self.login.data).first()


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if form.validate_on_submit():
        user = form.get_user()
        login_user(user)
        flash('Logged in successfully.')
        return redirect('/admin/')

    return render_template("login.html", form=form)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.teardown_request
def shutdown_session(exception=None):
    db_session.remove()


if __name__ == '__main__':
    if not os.path.exists('/tmp/barbican.db'):
        app.logger.info('No database detected at /tmp/barbican.db. Creating one and the admin user.')
        init_db()
    app.run(debug=True)
