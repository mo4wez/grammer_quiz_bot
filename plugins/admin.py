from pyrogram import Client, filters
from pyrogram.types import Message
from models import User, QuizAttempt, UserAnswer
from peewee import fn
import datetime

# List of admin user IDs (Telegram IDs of users who can access admin commands)
ADMIN_USER_IDS = [652429947]

# Admin filter - only allow commands from admin users
def admin_filter(_, __, message):
    return message.from_user and message.from_user.id in ADMIN_USER_IDS

admin_only = filters.create(admin_filter)

@Client.on_message(filters.command("admin") & admin_only)
async def admin_command(client: Client, message: Message):
    """Show admin commands help"""
    await message.reply_text(
        "🔐 **Admin Commands**\n\n"
        "/admin - Show this help message\n"
        "/users - Show total user count and recent users\n"
        "/user_stats <user_id> - Show detailed stats for a specific user\n"
        "/global_stats - Show global statistics for the bot\n"
        "/active_users - Show most active users by quiz count\n"
        "/top_scores - Show users with highest scores"
    )

@Client.on_message(filters.command("users") & admin_only)
async def users_command(client: Client, message: Message):
    """Show total user count and recent users"""
    total_users = User.select().count()
    recent_users = User.select().order_by(User.joined_date.desc()).limit(10)
    
    user_list = "\n".join(
        f"{i+1}. {user.first_name} {user.last_name or ''} (@{user.username or 'No username'}) - "
        f"ID: {user.user_id} - Joined: {user.joined_date.strftime('%Y-%m-%d')}"
        for i, user in enumerate(recent_users)
    )
    
    await message.reply_text(
        f"👥 **User Statistics**\n\n"
        f"Total registered users: {total_users}\n\n"
        f"**Most recent users:**\n{user_list}"
    )

@Client.on_message(filters.command("user_stats") & admin_only)
async def user_stats_command(client: Client, message: Message):
    """Show detailed stats for a specific user"""
    # Check if user ID is provided
    command_parts = message.text.split()
    if len(command_parts) < 2:
        await message.reply_text("Please provide a user ID. Example: /user_stats 123456789")
        return
    
    try:
        user_id = int(command_parts[1])
    except ValueError:
        await message.reply_text("Invalid user ID. Please provide a numeric ID.")
        return
    
    # Get user
    try:
        user = User.get(User.user_id == user_id)
    except User.DoesNotExist:
        await message.reply_text(f"User with ID {user_id} not found.")
        return
    
    # Get quiz attempts
    quiz_attempts = QuizAttempt.select().where(QuizAttempt.user == user)
    completed_quizzes = quiz_attempts.where(QuizAttempt.end_time.is_null(False))
    
    # Calculate statistics
    total_attempts = quiz_attempts.count()
    completed_count = completed_quizzes.count()
    
    if completed_count > 0:
        avg_score = sum(q.score for q in completed_quizzes) / completed_count
        best_score = max((q.score for q in completed_quizzes), default=0)
        total_questions_answered = UserAnswer.select().join(QuizAttempt).where(QuizAttempt.user == user).count()
        correct_answers = UserAnswer.select().join(QuizAttempt).where(
            (QuizAttempt.user == user) & (UserAnswer.is_correct == True)
        ).count()
        accuracy = (correct_answers / total_questions_answered * 100) if total_questions_answered > 0 else 0
    else:
        avg_score = 0
        best_score = 0
        total_questions_answered = 0
        correct_answers = 0
        accuracy = 0
    
    # Get recent activity
    last_activity = quiz_attempts.order_by(QuizAttempt.start_time.desc()).first()
    last_activity_time = last_activity.start_time if last_activity else "Never"
    
    await message.reply_text(
        f"📊 **User Details**\n\n"
        f"User: {user.first_name} {user.last_name or ''}\n"
        f"Username: @{user.username or 'None'}\n"
        f"User ID: {user.user_id}\n"
        f"Joined: {user.joined_date.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"**Quiz Statistics:**\n"
        f"Total quiz attempts: {total_attempts}\n"
        f"Completed quizzes: {completed_count}\n"
        f"Average score: {avg_score:.1f}\n"
        f"Best score: {best_score}\n"
        f"Questions answered: {total_questions_answered}\n"
        f"Correct answers: {correct_answers}\n"
        f"Accuracy: {accuracy:.1f}%\n\n"
        f"Last activity: {last_activity_time}"
    )

@Client.on_message(filters.command("global_stats") & admin_only)
async def global_stats_command(client: Client, message: Message):
    """Show global statistics for the bot"""
    total_users = User.select().count()
    total_quizzes = QuizAttempt.select().count()
    completed_quizzes = QuizAttempt.select().where(QuizAttempt.end_time.is_null(False)).count()
    total_questions = UserAnswer.select().count()
    correct_answers = UserAnswer.select().where(UserAnswer.is_correct == True).count()
    
    # Calculate global accuracy
    accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    
    # Get average score
    avg_score_query = QuizAttempt.select(fn.AVG(QuizAttempt.score)).where(QuizAttempt.end_time.is_null(False))
    avg_score = avg_score_query.scalar() or 0
    
    # Get users registered in the last 7 days
    week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    new_users = User.select().where(User.joined_date >= week_ago).count()
    
    # Get quizzes taken in the last 7 days
    recent_quizzes = QuizAttempt.select().where(QuizAttempt.start_time >= week_ago).count()
    
    await message.reply_text(
        f"📈 **Global Statistics**\n\n"
        f"**User Stats:**\n"
        f"Total users: {total_users}\n"
        f"New users (last 7 days): {new_users}\n\n"
        f"**Quiz Stats:**\n"
        f"Total quizzes started: {total_quizzes}\n"
        f"Completed quizzes: {completed_quizzes}\n"
        f"Quizzes taken (last 7 days): {recent_quizzes}\n"
        f"Average score: {avg_score:.1f}\n\n"
        f"**Question Stats:**\n"
        f"Total questions answered: {total_questions}\n"
        f"Correct answers: {correct_answers}\n"
        f"Global accuracy: {accuracy:.1f}%"
    )

@Client.on_message(filters.command("active_users") & admin_only)
async def active_users_command(client: Client, message: Message):
    """Show most active users by quiz count"""
    # Get users with the most quiz attempts
    query = (
        User
        .select(User, fn.COUNT(QuizAttempt.id).alias('quiz_count'))
        .join(QuizAttempt)
        .group_by(User.id)
        .order_by(fn.COUNT(QuizAttempt.id).desc())
        .limit(10)
    )
    
    if not query.exists():
        await message.reply_text("No quiz attempts recorded yet.")
        return
    
    user_list = "\n".join(
        f"{i+1}. {user.first_name} {user.last_name or ''} (@{user.username or 'No username'}) - "
        f"{user.quiz_count} quizzes"
        for i, user in enumerate(query)
    )
    
    await message.reply_text(
        f"🏆 **Most Active Users**\n\n{user_list}"
    )

@Client.on_message(filters.command("top_scores") & admin_only)
async def top_scores_command(client: Client, message: Message):
    """Show users with highest scores"""
    # Get top quiz scores
    top_scores = (
        QuizAttempt
        .select(QuizAttempt, User)
        .join(User)
        .where(QuizAttempt.end_time.is_null(False))
        .order_by(QuizAttempt.score.desc())
        .limit(10)
    )
    
    if not top_scores.exists():
        await message.reply_text("No completed quizzes yet.")
        return
    
    score_list = "\n".join(
        f"{i+1}. {attempt.user.first_name} {attempt.user.last_name or ''} - "
        f"Score: {attempt.score}/{attempt.total_questions} "
        f"({attempt.score/attempt.total_questions*100:.1f}%)"
        for i, attempt in enumerate(top_scores)
    )
    
    await message.reply_text(
        f"🥇 **Top Quiz Scores**\n\n{score_list}"
    )