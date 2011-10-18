from fullerene import app, CONFIG


app.run(host='localhost', port=8080, debug=True, extra_files=(CONFIG,))
