
from flask import Flask, render_template, flash, \
    url_for, redirect, request, session
import cx_Oracle as oracle
from scripts import credentials, loader
from wtforms import Form, BooleanField, TextField, PasswordField, \
    validators, ValidationError, SelectField


app = Flask(__name__)
app.config.from_object('flask_settings')


# Opens SQL*Plus db and cursor connections
def connect_db():
    db = oracle.connect("{}/{}@{}".format(credentials.username,
                                          credentials.password,
                                          credentials.server))
    cursor = db.cursor()
    return db, cursor


# Closes SQL*Plus db and cursor connections
def close_db(db, cursor):
    cursor.close()
    db.close()


def populate_cookie(user_id):
    db, cursor = connect_db()

    #get all strategies
    session.pop('strategy', None)
    cursor.execute("SELECT S.strategy_id, S.strategy_name FROM create_strategy C, strategy S WHERE " +
                   "C.strategy_id = S.strategy_id AND C.user_id = '{}'".format(user_id))
    data = cursor.fetchall()
    strategies = []
    for strat in data:
        strategies.append((strat[0], strat[1]))
        print strategies
    if len(strategies) > 0:
        session['strategy'] = strategies

    #get all indicators
    for strat in session['strategy']:
        cursor.execute("SELECT indicator_id FROM criteria WHERE " +
                       "strategy_id = '{}'".format(strat[0]))
        for ind in cursor.fetchall():
            print ind
            if 'indicator' in session:
                session['indicator'].append(ind[0])
            else:
                session['indicator'] = [ind[0]]


def get_session():
    return session


def add_data(table_name, data):
    loader.insert_data(table_name, data)


def get_next_index(table_name, colum_name):
    sql_query = "SELECT MAX({}) FROM {}".format(colum_name,
                                                table_name)
    db, cursor = connect_db()
    cursor.execute(sql_query)
    max_index = int(cursor.fetchall()[0][0])
    return max_index+1


def check_if_logged_in():
    if 'user_id' not in session:
        flash('Please log in before making a strategy!')
        return redirect(url_for('log_in'))


def check_for_objects(table_name):
    sql_query = "SELECT COUNT(*) FROM {}".format(table_name)
    db, cursor = connect_db()
    cursor.execute(sql_query)
    num = int(cursor.fetchall()[0][0])
    close_db(db, cursor)
    return num


@app.errorhandler(404)
def not_found(error):
    return render_template('error.html')


#####################################################################
# Create Indicator form
#####################################################################
def CreateIndicatorForm():
    class Create_Indicator_Form(Form):
        security = TextField('Ticker Name', [
                             validators.Required(),
                             validators.Length(min=1, max=6)])
        mva_10 = BooleanField('10 day moving average')
        mva_25 = BooleanField('25 day moving average')
        strategy = SelectField('strategy', choices=session['strategy'])

        def validate_mva_10(form, field):
            if form.mva_25.data is True and field.data is True:
                raise ValidationError('You can only choose one reference')
            if form.mva_25.data is False and field.data is False:
                raise ValidationError('You must choose at least one reference')
    return Create_Indicator_Form(request.form)


@app.route('/create_indicator', methods=['GET', 'POST'])
def create_indicator():
    check_if_logged_in()
    create_indicator_form = CreateIndicatorForm()
    print 'HERE', type(create_indicator_form)

    print session['strategy']

    if request.method == 'POST' and create_indicator_form.validate():
        indicator_id = get_next_index('indicator', 'indicator_id')
        ticker = create_indicator_form.security.data
        if create_indicator_form.mva_10.data is True:
            mva_10_day = 'Y'
            mva_25_day = 'N'
        else:
            mva_10_day = 'N'
            mva_25_day = 'Y'
        row = [indicator_id, ticker, mva_10_day, mva_25_day]
        add_data('indicator', row)
        # adding relation
        criteria_row = [session['strategy'][0], indicator_id]
        add_data('criteria', criteria_row)
        return redirect(url_for('home'))

    return render_template('create_indicator.html',
                           form=create_indicator_form)


#####################################################################
# Create Strategy
#####################################################################
class Create_Strategy_Form(Form):
    strat_name = TextField('Strategy Name', [
        validators.Required(),
        validators.Length(min=10, max=200)])


@app.route('/create_strategy', methods=['GET', 'POST'])
def create_strategy():
    check_if_logged_in()
    create_strat_form = Create_Strategy_Form(request.form)
    if request.method == 'POST' and create_strat_form.validate():
        strat_id = get_next_index('strategy', 'strategy_id')
        strat_name = create_strat_form.strat_name.data
        strat = [strat_id, strat_name]
        add_data('strategy', strat)
        add_data('create_strategy', [session['user_id'], strat_id])

        if 'strategy' in session:
            session['strategy'].append(strat_id)
        else:
            session['strategy'] = [strat_id]
        flash('New strategy, {}, created'.format(strat_name))
        return redirect(url_for('home'))

    return render_template('create_strategy.html',
                           form=create_strat_form)


#####################################################################
# Log In
#####################################################################
class Log_in_Form(Form):
    username = TextField('Username')
    password = PasswordField('Password')

    def validate_username(form, field):
        sql_query = """
        SELECT user_id
        FROM
            user_data
        WHERE
            user_id = '{}' """.format(field.data)
        db, cursor = connect_db()
        data = cursor.execute(sql_query).fetchall()
        close_db(db, cursor)
        if len(data) != 1:
            raise ValidationError("Wrong username")

    def validate_password(form, field):
        sql_query = """
        SELECT password
        FROM
            user_data
        WHERE
            user_id = '{}' """.format(form.username.data)
        db, cursor = connect_db()
        data = cursor.execute(sql_query).fetchall()
        close_db(db, cursor)
        if data[0][0] != field.data:
            raise ValidationError('Wrong password')


@app.route('/log_in', methods=['GET', 'POST'])
def log_in():
    log_in_form = Log_in_Form(request.form)
    if request.method == 'POST' and log_in_form.validate():
        session['user_id'] = log_in_form.username.data
        flash("You're logged in as {}".format(session['user_id']))
        populate_cookie(log_in_form.username.data)
        return redirect(url_for('home'))

    return render_template('log_in.html', form=log_in_form)


#####################################################################
#Register User
#####################################################################
class Register_Form(Form):
    username = TextField('Username')
    password = PasswordField('New Password', [
        validators.Required(),
        validators.EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Confirm Password')
    accept_tos = BooleanField('I accept the terms of service', [
                              validators.Required()])

    def validate_username(form, field):
        if len(field.data) > 20 or len(field.data) < 4:
            raise ValidationError('Username must between 5 and 20 ' +
                                  'characters')
        sql_query = """
        SELECT *
        FROM
            user_data
        WHERE
            user_id = '{}'""".format(field.data)
        db, cursor = connect_db()
        data = cursor.execute(sql_query).fetchall()
        close_db(db, cursor)
        if len(data) is 1:
            raise ValidationError('Username already in use')


@app.route('/register', methods=['GET', 'POST'])
def register():
    reg_form = Register_Form(request.form)
    if request.method == 'POST' and reg_form.validate():
        user = [reg_form.username.data, reg_form.password.data]
        add_data('user_data', user)
        flash('Thanks for registering, {}'.format(user[0]))
        return redirect(url_for('home'))
    return render_template('register.html', form=reg_form)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))


@app.route('/')
def home():
    return render_template('home.html')


if __name__ == '__main__':
    app.run()
