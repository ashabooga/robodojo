from bottle import route, run,  install, template
from ml import pred



@route('/hello')
def hello():
	return "Hello World!"

@route('/')

@route('/hello/<name>')
def greet(name='Stranger'):
	return template('Hello {{name}}, how are you?', name=name)

@route('/predict/<teams>')
def predict(teams="4174-4174-4174-4174"):
	prediction = pred(teams)
	return template(prediction)

run(host='localhost', port=11000, debug=True)