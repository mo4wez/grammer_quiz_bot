from peewee import *
import datetime

# Create a SQLite database
db = SqliteDatabase('grammar_bot.db')

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    user_id = IntegerField(unique=True)
    username = CharField(null=True)
    first_name = CharField()
    last_name = CharField(null=True)
    joined_date = DateTimeField(default=datetime.datetime.now)

class QuizAttempt(BaseModel):
    user = ForeignKeyField(User, backref='quiz_attempts')
    start_time = DateTimeField(default=datetime.datetime.now)
    end_time = DateTimeField(null=True)
    score = IntegerField(default=0)
    total_questions = IntegerField(default=0)

class UserAnswer(BaseModel):
    quiz_attempt = ForeignKeyField(QuizAttempt, backref='answers')
    question_id = IntegerField()
    selected_option = IntegerField(null=True)  # Null if no answer was given
    is_correct = BooleanField(null=True)
    answer_time = DateTimeField(null=True)  # Time when the user answered

def create_tables():
    with db:
        db.create_tables([User, QuizAttempt, UserAnswer])

if __name__ == '__main__':
    create_tables()