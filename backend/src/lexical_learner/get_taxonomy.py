# backend/src/lexical_learner/get_taxonomy.py
# Expose the current category, topic and subtopic tree as a read-only LangChain tool.
# Tests: backend/tests/test_get_taxonomy.py

from typing import TypedDict

from langchain_core.tools import tool

from lexical_learner.database import connect_database


class Subtopic(TypedDict):
    id: str
    name: str
    description: str


class Topic(Subtopic):
    subtopics: list[Subtopic]


class Category(Subtopic):
    topics: list[Topic]


@tool
def get_taxonomy() -> list[Category]:
    """List all existing categories, topics and subtopics with IDs, names and descriptions.

    Read this tree before proposing new learning topics or classifying a scenario.
    A scenario may belong directly to a topic; a subtopic is optional.
    This tool only reads PostgreSQL and never calls an LLM or changes data.
    """
    with connect_database() as connection:
        categories = connection.execute(
            "SELECT id, name, description FROM categories ORDER BY name, id"
        ).fetchall()
        topics = connection.execute(
            "SELECT id, category_id, name, description FROM topics ORDER BY name, id"
        ).fetchall()
        subtopics = connection.execute(
            "SELECT id, topic_id, name, description FROM subtopics ORDER BY name, id"
        ).fetchall()

    result: list[Category] = []
    by_category: dict[str, Category] = {}
    by_topic: dict[str, Topic] = {}
    for category_id, name, description in categories:
        category = Category(id=category_id, name=name, description=description, topics=[])
        result.append(category)
        by_category[category_id] = category
    for topic_id, category_id, name, description in topics:
        topic = Topic(id=topic_id, name=name, description=description, subtopics=[])
        by_category[category_id]["topics"].append(topic)
        by_topic[topic_id] = topic
    for subtopic_id, topic_id, name, description in subtopics:
        by_topic[topic_id]["subtopics"].append(
            Subtopic(id=subtopic_id, name=name, description=description)
        )
    return result
