from flask import Flask, render_template, request, jsonify
import datetime

app = Flask(__name__)

# In-memory storage (replace with a database in production)
posts = []

@app.route('/')
def index():
    return render_template('index2.html', posts=reversed(posts)) #show newest posts first

@app.route('/create_post', methods=['POST'])
def create_post():
    data = request.get_json()
    content = data.get('content')
    if content:
        post = {
            'id': len(posts) + 1,
            'content': content,
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        posts.append(post)
        return jsonify({'message': 'Post created successfully'}), 201
    else:
        return jsonify({'error': 'Content is required'}), 400

@app.route('/get_posts', methods=['GET'])
def get_posts():
    return jsonify(list(reversed(posts))) #show newest posts first.

if __name__ == '__main__':
    app.run(debug=True)

