from bottle import route, run,  install, template
# from bottle_sqlite import SQLitePlugin

# install(SQLitePlugin(dbfile='/tmp/test.db'))

@route('/hello')
def hello():
    return "Hello World!"

@route('/')

@route('/hello/<name>')
def greet(name='Stranger'):
    return template('Hello {{name}}, how are you?', name=name)

run(host='localhost', port=11000, debug=True)