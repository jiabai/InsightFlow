import logging
import json
from sqlalchemy.ext.asyncio import AsyncSession
from be.common.database_manager import DatabaseManager
from be.llm_knowledge_processing.llm_client import LLMClient
from be.llm_knowledge_processing.utils import (
    extract_json_from_llm_output,
    get_question_prompt,
    random_remove_question_mark,
    get_add_label_prompt
)

logger = logging.getLogger(__name__)

class QuestionGenerator:
    def __init__(self, llm_config: dict, db_manager: DatabaseManager, is_mock: bool=True):
        self.llm_client = LLMClient(llm_config, is_mock)
        self.db_manager = db_manager

    async def generate_for_chunk(
        self,
        content: str,
        project_config: dict,
        project_details: dict,
        tags: list
    ) -> list[dict[str, str]]:
        questions = self._generate_raw_questions(content, project_config, project_details)
        if not questions:
            return None

        questions = self._process_questions(questions, project_config)
        logger.debug("Generated %d questions: %s", len(questions), questions)

        if not tags:
            labeled_questions = [{'question': q} for q in questions]
            logger.info(
                "Successfully generated and created %d questions.",
                len(labeled_questions)
            )
            return labeled_questions

        return await self._label_and_save_questions(questions, tags)

    async def _get_chunk_content(self, db: AsyncSession, chunk_id: str):
        chunk = await self.db_manager.get_chunk_by_id(db, chunk_id)
        return chunk.content if chunk else None

    def _generate_raw_questions(self, content, project_config, project_details):
        question_gen_length = project_config.get('questionGenerationLength', 500)
        number_of_questions = max(1, int(len(content) / question_gen_length))
        logger.debug(
            "Generating %d questions, content length: %d, question length: %d",
            number_of_questions,
            len(content),
            question_gen_length
        )
        question_prompt = get_question_prompt(
            text=content,
            number=number_of_questions,
            language=project_config.get('language', '中文'),
            global_prompt=project_details.get('globalPrompt', ''),
            question_prompt=project_details.get('questionPrompt', '')
        )
        raw_response = self.llm_client.get_response(question_prompt)
        return extract_json_from_llm_output(raw_response)

    def _process_questions(self, questions, project_config):
        return random_remove_question_mark(
            questions,
            project_config.get('questionMaskRemovingProbability', 60)
        )

    async def _label_and_save_questions(
        self,
        questions: list[dict[str, str]],
        tags: list[dict[str, str]]
    ):
        tags_json = json.dumps([tag['name'] for tag in tags], ensure_ascii=False)
        questions_json = json.dumps(questions, ensure_ascii=False)
        label_prompt = get_add_label_prompt(tags_json, questions_json)
        labeled_response = self.llm_client.get_response(label_prompt)
        labeled_questions = extract_json_from_llm_output(labeled_response)

        if not labeled_questions:
            logger.warning("Failed to add labels to questions. Using unlabelled questions.")
            labeled_questions = [{'question': q, 'label': 'unlabelled'} for q in questions]
        return labeled_questions
