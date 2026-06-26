# Copyright 2026 Google LLC
# MCP Server for EduPath Agent

from fastmcp import FastMCP

mcp = FastMCP("EduPath MCP Server")

@mcp.tool()
def search_courses(query: str, subject: str) -> list[dict]:
    """Search for courses or articles related to a subject and query.

    Args:
        query: Specific search terms (e.g., "pandas dataframe").
        subject: The broader subject name (e.g., "Python").
    """
    courses = [
        {"title": "Intro to Python for Beginners", "url": "https://www.coursera.org/learn/python-basics", "provider": "Coursera", "difficulty": "beginner"},
        {"title": "Intermediate Python Programming", "url": "https://www.udemy.com/course/intermediate-python/", "provider": "Udemy", "difficulty": "intermediate"},
        {"title": "Data Science Foundations in Python", "url": "https://www.edx.org/course/data-science-python", "provider": "edX", "difficulty": "intermediate"},
        {"title": "Advanced Python & Software Design", "url": "https://realpython.com/", "provider": "RealPython", "difficulty": "advanced"},
        {"title": "Automate the Boring Stuff with Python", "url": "https://automatetheboringstuff.com/", "provider": "Al Sweigart", "difficulty": "beginner"},
    ]
    results = []
    for c in courses:
        if query.lower() in c["title"].lower() or subject.lower() in c["title"].lower():
            results.append(c)
    return results if results else courses[:2]

@mcp.tool()
def get_learning_tips(subject: str, experience_level: str) -> str:
    """Get customized learning tips for a specific subject and experience level.

    Args:
        subject: The learning subject (e.g. "Math", "Python").
        experience_level: Level of experience (beginner, intermediate, advanced).
    """
    tips = {
        "beginner": "Focus on daily active coding (even 20 mins) rather than long reading. Use spaced repetition for syntax concepts.",
        "intermediate": "Transition from syntax to building small personal projects. Focus on testing and debugging your code.",
        "advanced": "Focus on system design, architecture, and code performance. Contribute to open source or build libraries."
    }
    level = experience_level.lower()
    t = tips.get(level, tips["beginner"])
    return f"Learning Strategy for {experience_level} in {subject}: {t}"

@mcp.tool()
def calculate_study_schedule(available_hours: int, difficulty: str) -> dict:
    """Calculate the estimated weeks and hours needed to achieve a goal.

    Args:
        available_hours: Number of hours the student can commit per week.
        difficulty: Expected topic difficulty (easy, medium, hard).
    """
    total_hours_required = {"easy": 40, "medium": 80, "hard": 150}
    hours = total_hours_required.get(difficulty.lower(), 80)
    weeks = max(1, round(hours / max(1, available_hours)))
    return {
        "difficulty": difficulty,
        "total_hours_required": hours,
        "estimated_weeks": weeks,
        "hours_per_week": available_hours
    }

if __name__ == "__main__":
    mcp.run(transport="stdio")
