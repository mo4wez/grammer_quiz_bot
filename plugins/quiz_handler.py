import json
import asyncio
import datetime
import random  # Add this import
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from models import User, QuizAttempt, UserAnswer

# Load questions from JSON file
with open("questions.json", "r") as f:
    ALL_QUESTIONS = json.load(f)["questions"]  # Renamed to ALL_QUESTIONS

# Store active quiz sessions
active_quizzes = {}

async def countdown(message, user_id):
    """Display a countdown before starting the quiz"""
    for i in range(3, 0, -1):
        await message.edit_text(f"Quiz starting in {i}...")
        await asyncio.sleep(1)
    await message.edit_text("Quiz starting now!")
    await asyncio.sleep(1)
    
    # Start the quiz
    await send_question(message, user_id, 0)

async def send_question(message, user_id, question_index):
    """Send a question to the user"""
    # Get the user's randomized questions
    user_questions = active_quizzes[user_id]["questions"]
    
    if question_index >= len(user_questions):
        # Quiz completed
        await end_quiz(message, user_id)
        return
    
    question = user_questions[question_index]
    options = question["options"]
    
    # Create inline keyboard with options
    keyboard = []
    
    # Add time counter button at the top (non-functional, just for display)
    keyboard.append([InlineKeyboardButton(
        "⏱ Time remaining: 15s", 
        callback_data="timer_info"
    )])
    
    # Add a separator
    keyboard.append([InlineKeyboardButton(
        "------------------------", 
        callback_data="separator"
    )])
    
    # Add option buttons
    for i, option in enumerate(options):
        keyboard.append([InlineKeyboardButton(
            f"{chr(65+i)}. {option}", 
            callback_data=f"answer_{question_index}_{i}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send the question with time indicator
    quiz_message = await message.edit_text(
        f"Question {question_index + 1}/{len(user_questions)}:\n\n"
        f"{question['question']}\n\n"
        f"_Time remaining: 15 seconds_",  # Italic text for time
        reply_markup=reply_markup
    )
    
    # Store the current question in active quizzes
    active_quizzes[user_id]["current_question"] = question_index
    active_quizzes[user_id]["message_id"] = quiz_message.id
    active_quizzes[user_id]["start_time"] = datetime.datetime.now()  # Track when question started
    
    # Set a timer for this question and update the countdown
    asyncio.create_task(update_time_counter(message, user_id, question_index))

async def update_time_counter(message, user_id, question_index):
    """Update the time counter every second"""
    # Total time for question in seconds
    total_time = 15
    
    # Update every second
    for remaining in range(total_time - 1, 0, -1):
        # Check if user is still on this question
        if (user_id not in active_quizzes or 
            active_quizzes[user_id]["current_question"] != question_index):
            # User already answered or moved on
            return
        
        # Wait 1 second
        await asyncio.sleep(1)
        
        # Get user's questions
        user_questions = active_quizzes[user_id]["questions"]
        question = user_questions[question_index]
        options = question["options"]
        
        # Update keyboard with new time
        keyboard = []
        
        # Update time counter button
        time_text = f"⏱ Time remaining: {remaining}s"
        keyboard.append([InlineKeyboardButton(
            time_text, 
            callback_data="timer_info"
        )])
        
        # Add a separator
        keyboard.append([InlineKeyboardButton(
            "------------------------", 
            callback_data="separator"
        )])
        
        # Add option buttons
        for i, option in enumerate(options):
            keyboard.append([InlineKeyboardButton(
                f"{chr(65+i)}. {option}", 
                callback_data=f"answer_{question_index}_{i}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Update the message with new time
        try:
            await message.edit_text(
                f"Question {question_index + 1}/{len(user_questions)}:\n\n"
                f"{question['question']}\n\n"
                f"_Time remaining: {remaining} seconds_",  # Italic text for time
                reply_markup=reply_markup
            )
        except Exception as e:
            # Handle potential errors (e.g., message couldn't be edited)
            print(f"Error updating timer: {e}")
            break
    
    # Time's up - handle as in the original question_timer function
    await question_timer(message, user_id, question_index)

async def question_timer(message, user_id, question_index):
    """Timer for each question (15 seconds)"""
    # Check if the user is still on this question
    if (user_id in active_quizzes and 
        active_quizzes[user_id]["current_question"] == question_index):
        
        # User didn't answer in time
        quiz_attempt_id = active_quizzes[user_id]["quiz_attempt_id"]
        user_questions = active_quizzes[user_id]["questions"]
        
        # Record the non-answer
        UserAnswer.create(
            quiz_attempt=quiz_attempt_id,
            question_id=user_questions[question_index]["id"],
            selected_option=None,
            is_correct=False,
            answer_time=None
        )
        
        # Show time's up message briefly
        try:
            await message.edit_text(
                f"Question {question_index + 1}/{len(user_questions)}:\n\n"
                f"{user_questions[question_index]['question']}\n\n"
                f"**Time's up!**"
            )
            await asyncio.sleep(1)  # Show the time's up message briefly
        except Exception:
            pass  # Ignore errors here
        
        # Move to the next question
        await send_question(message, user_id, question_index + 1)

# Add handler for timer button clicks to prevent errors
@Client.on_callback_query(filters.regex(r'^timer_info|separator$'))
async def handle_timer_click(client: Client, callback_query: CallbackQuery):
    """Handle clicks on the timer button (just show a notification)"""
    await callback_query.answer("This is just a timer display")

async def end_quiz(message, user_id):
    """End the quiz and show results"""
    if user_id not in active_quizzes:
        return
    
    quiz_attempt_id = active_quizzes[user_id]["quiz_attempt_id"]
    quiz_attempt = QuizAttempt.get_by_id(quiz_attempt_id)
    user_questions = active_quizzes[user_id]["questions"]
    
    # Update the quiz attempt
    quiz_attempt.end_time = datetime.datetime.now()
    quiz_attempt.save()
    
    # Calculate the score
    correct_answers = UserAnswer.select().where(
        (UserAnswer.quiz_attempt == quiz_attempt_id) & 
        (UserAnswer.is_correct == True)
    ).count()
    
    total_questions = len(user_questions)
    quiz_attempt.score = correct_answers
    quiz_attempt.total_questions = total_questions
    quiz_attempt.save()
    
    # Show results
    await message.edit_text(
        f"Quiz completed!\n\n"
        f"Your score: {correct_answers}/{total_questions}\n\n"
        f"Thank you for taking the Passive Voice Grammar Quiz!"
    )
    
    # Clean up
    del active_quizzes[user_id]

@Client.on_message(filters.command("quiz"))
async def quiz_command(client: Client, message: Message):
    """Handle the /quiz command"""
    user_id = message.from_user.id
    
    # Check if user is already in a quiz
    if user_id in active_quizzes:
        await message.reply_text("You already have an active quiz. Please finish it first.")
        return
    
    # Get or create user
    user, created = User.get_or_create(
        user_id=user_id,
        defaults={
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name
        }
    )
    
    # Create a new quiz attempt
    quiz_attempt = QuizAttempt.create(
        user=user,
        start_time=datetime.datetime.now()
    )
    
    # Create a randomized copy of questions for this user
    user_questions = ALL_QUESTIONS.copy()
    random.shuffle(user_questions)
    
    # Initialize the quiz session
    active_quizzes[user_id] = {
        "quiz_attempt_id": quiz_attempt.id,
        "current_question": -1,
        "message_id": None,
        "questions": user_questions  # Store the randomized questions
    }
    
    # Send welcome message
    welcome_message = await message.reply_text(
        f"Welcome to the Passive Voice Grammar Quiz, {message.from_user.first_name}!\n\n"
        f"You will be presented with {len(user_questions)} questions about passive voice in English grammar.\n"
        f"Each question has a 15-second time limit.\n\n"
        f"Get ready!"
    )
    
    # Start countdown
    await countdown(welcome_message, user_id)

@Client.on_callback_query(filters.regex(r'^answer_(\d+)_(\d+)$'))
async def handle_quiz_answer(client: Client, callback_query: CallbackQuery):
    """Handle quiz answer callbacks"""
    user_id = callback_query.from_user.id
    
    # Check if the user has an active quiz
    if user_id not in active_quizzes:
        await callback_query.answer("No active quiz found. Please start a new one with /quiz")
        return
    
    # Parse the callback data
    parts = callback_query.data.split("_")
    question_index = int(parts[1])
    selected_option = int(parts[2])
    
    # Check if this is the current question
    if active_quizzes[user_id]["current_question"] != question_index:
        await callback_query.answer("This question has already been answered or timed out")
        return
    
    # Get the user's questions and the correct answer
    user_questions = active_quizzes[user_id]["questions"]
    correct_answer = user_questions[question_index]["correct_answer"]
    is_correct = (selected_option == correct_answer)
    
    # Record the answer
    quiz_attempt_id = active_quizzes[user_id]["quiz_attempt_id"]
    UserAnswer.create(
        quiz_attempt=quiz_attempt_id,
        question_id=user_questions[question_index]["id"],
        selected_option=selected_option,
        is_correct=is_correct,
        answer_time=datetime.datetime.now()
    )
    
    # Provide feedback
    feedback = "✅ Correct!" if is_correct else "❌ Incorrect!"
    await callback_query.answer(feedback)
    
    # Move to the next question
    await send_question(callback_query.message, user_id, question_index + 1)