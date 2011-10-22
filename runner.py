from fullerene import app, CONFIG


app.run(host='0.0.0.0', port=8080, debug=True, extra_files=(CONFIG,))
