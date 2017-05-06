# Created by liuchuang on 2017/3/15.
from litemp import Litemp, LitempSyntaxError

lite = Litemp('''
            <h1>Hello {{name|upper}}!</h1>
            {% for topic in topics %}
                <p>You are interested in {{topic}}.</p>
            {% endfor %}
            ''',
              {'upper': str.upper},
              )
text = lite.render({'name': "Ned",
                    'topics': ['Python', 'Geometry', 'Juggling']
                    })
print(text)
