from pyrogram import Client, filters
from pyrogram.types import Message
from models import User, QuizAttempt

@Client.on_message(filters.command("stats"))
async def stats_command(client: Client, message: Message):
    """Handle the /stats command"""
    user_id = message.from_user.id
    
    # Get user
    try:
        user = User.get(User.user_id == user_id)
    except User.DoesNotExist:
        await message.reply_text("You haven't taken any quizzes yet. Use /quiz to start one.")
        return
    
    # Get quiz attempts
    quiz_attempts = QuizAttempt.select().where(QuizAttempt.user == user)
    
    if quiz_attempts.count() == 0:
        await message.reply_text("You haven't taken any quizzes yet. Use /quiz to start one.")
        return
    
    # Calculate statistics
    total_attempts = quiz_attempts.count()
    completed_attempts = quiz_attempts.where(QuizAttempt.end_time.is_null(False)).count()
    total_score = sum(attempt.score for attempt in quiz_attempts if attempt.end_time)
    total_questions = sum(attempt.total_questions for attempt in quiz_attempts if attempt.end_time)
    
    if total_questions > 0:
        accuracy = (total_score / total_questions) * 100
    else:
        accuracy = 0
    
    # Get best score
    best_attempt = quiz_attempts.where(QuizAttempt.end_time.is_null(False)).order_by(QuizAttempt.score.desc()).first()
    best_score = best_attempt.score if best_attempt else 0
    
    # Send statistics
    await message.reply_text(
        f"📊 **Your Statistics**\n\n"
        f"Total quiz attempts: {total_attempts}\n"
        f"Completed quizzes: {completed_attempts}\n"
        f"Best score: {best_score}/{best_attempt.total_questions if best_attempt else 0}\n"
        f"Overall accuracy: {accuracy:.1f}%\n\n"
        f"Keep practicing to improve your passive voice grammar skills!"
    )