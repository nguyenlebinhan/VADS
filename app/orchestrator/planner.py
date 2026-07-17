from __future__ import annotations

from app.model_gateway.router import ModelRouter
from app.model_gateway.schemas import RoutingRequest, TaskType
from app.orchestrator.schemas import ExecutionPlan, ExecutionStep, WorkflowIntent


class ExecutionPlanner:
    def __init__(self, router: ModelRouter) -> None:
        self.router = router

    def summary_plan(self, document_id: str, *, private: bool = False) -> ExecutionPlan:
        return ExecutionPlan(
            intent=WorkflowIntent.DOCUMENT_SUMMARY,
            documentId=document_id,
            privateProcessing=private,
            steps=[
                self._model_step(
                    "generate-summary",
                    TaskType.DOCUMENT_SUMMARY,
                    "DocumentSummaryOutput",
                    private=private,
                    parallel=True,
                )
            ],
        )

    def knowledge_graph_plan(
        self,
        document_id: str,
        *,
        private: bool = False,
    ) -> ExecutionPlan:
        return ExecutionPlan(
            intent=WorkflowIntent.KNOWLEDGE_GRAPH_GENERATION,
            documentId=document_id,
            privateProcessing=private,
            steps=[
                self._model_step(
                    "extract-entities-relations",
                    TaskType.ENTITY_RELATION_EXTRACTION,
                    "GraphExtractionOutput",
                    private=private,
                    parallel=True,
                ),
                self._model_step(
                    "normalize-graph",
                    TaskType.ENTITY_NORMALIZATION,
                    "GraphExtractionOutput",
                    private=private,
                    depends_on=["extract-entities-relations"],
                ),
                self._model_step(
                    "verify-complex-relations",
                    TaskType.COMPLEX_RELATION_VERIFICATION,
                    "RelationVerificationOutput",
                    private=private,
                    depends_on=["normalize-graph"],
                ),
            ],
        )

    def critical_questions_plan(
        self,
        document_id: str,
        *,
        private: bool = False,
    ) -> ExecutionPlan:
        return ExecutionPlan(
            intent=WorkflowIntent.CRITICAL_QUESTION_GENERATION,
            documentId=document_id,
            privateProcessing=private,
            steps=[
                self._model_step(
                    "generate-critical-questions",
                    TaskType.CRITICAL_QUESTION_GENERATION,
                    "CriticalQuestionOutput",
                    private=private,
                ),
                self._model_step(
                    "verify-critical-questions",
                    TaskType.CRITICAL_QUESTION_VERIFICATION,
                    "QuestionVerificationOutput",
                    private=private,
                    depends_on=["generate-critical-questions"],
                ),
            ],
        )

    def red_flag_plan(self, document_id: str, *, private: bool = False) -> ExecutionPlan:
        return ExecutionPlan(
            intent=WorkflowIntent.DOCUMENT_ANALYSIS,
            documentId=document_id,
            privateProcessing=private,
            steps=[
                ExecutionStep(
                    stepId="detect-red-flags",
                    taskType=TaskType.RED_FLAG_DETECTION,
                    executor="RULE_ENGINE",
                    reasonForSelection="Rule engine chạy bằng code trước LLM",
                    canRunInParallel=False,
                    timeoutSeconds=30,
                    maxRetries=0,
                    expectedOutputSchema="RedFlagOutput",
                ),
                self._model_step(
                    "verify-high-red-flags",
                    TaskType.RED_FLAG_VERIFICATION,
                    "RedFlagVerificationOutput",
                    private=private,
                    depends_on=["detect-red-flags"],
                ),
            ],
        )

    def analysis_plan(self, document_id: str, *, private: bool = False) -> ExecutionPlan:
        steps = [
            self._model_step(
                "generate-summary",
                TaskType.DOCUMENT_SUMMARY,
                "DocumentSummaryOutput",
                private=private,
                parallel=True,
            ),
            self._model_step(
                "extract-entities-relations",
                TaskType.ENTITY_RELATION_EXTRACTION,
                "GraphExtractionOutput",
                private=private,
                parallel=True,
            ),
            self._model_step(
                "normalize-graph",
                TaskType.ENTITY_NORMALIZATION,
                "GraphExtractionOutput",
                private=private,
                depends_on=["extract-entities-relations"],
            ),
            self._model_step(
                "verify-complex-relations",
                TaskType.COMPLEX_RELATION_VERIFICATION,
                "RelationVerificationOutput",
                private=private,
                depends_on=["normalize-graph"],
            ),
            ExecutionStep(
                stepId="detect-red-flags",
                taskType=TaskType.RED_FLAG_DETECTION,
                executor="RULE_ENGINE",
                reasonForSelection="Rule engine chạy bằng code trước LLM",
                dependsOn=["verify-complex-relations"],
                canRunInParallel=False,
                timeoutSeconds=30,
                maxRetries=0,
                expectedOutputSchema="RedFlagOutput",
            ),
            self._model_step(
                "verify-high-red-flags",
                TaskType.RED_FLAG_VERIFICATION,
                "RedFlagVerificationOutput",
                private=private,
                depends_on=["detect-red-flags"],
            ),
            self._model_step(
                "generate-critical-questions",
                TaskType.CRITICAL_QUESTION_GENERATION,
                "CriticalQuestionOutput",
                private=private,
                depends_on=["verify-high-red-flags"],
            ),
            self._model_step(
                "verify-critical-questions",
                TaskType.CRITICAL_QUESTION_VERIFICATION,
                "QuestionVerificationOutput",
                private=private,
                depends_on=["generate-critical-questions"],
            ),
        ]
        return ExecutionPlan(
            intent=WorkflowIntent.DOCUMENT_ANALYSIS,
            documentId=document_id,
            privateProcessing=private,
            steps=steps,
        )

    def cross_document_plan(
        self,
        document_ids: list[str],
        *,
        private: bool = False,
    ) -> ExecutionPlan:
        if len(document_ids) < 2:
            raise ValueError("Cross-document analysis requires at least two documents")
        return ExecutionPlan(
            intent=WorkflowIntent.CROSS_DOCUMENT_ANALYSIS,
            documentId=document_ids[0],
            documentIds=document_ids,
            privateProcessing=private,
            steps=[
                self._model_step(
                    "cross-document-analysis",
                    TaskType.CROSS_DOCUMENT_ANALYSIS,
                    "CrossDocumentAnalysisOutput",
                    private=private,
                )
            ],
        )

    def _model_step(
        self,
        step_id: str,
        task_type: TaskType,
        schema: str,
        *,
        private: bool,
        depends_on: list[str] | None = None,
        parallel: bool = False,
    ) -> ExecutionStep:
        decision = self.router.route(RoutingRequest(taskType=task_type, requirePrivate=private))
        return ExecutionStep(
            stepId=step_id,
            taskType=task_type,
            executor=decision.primary_model,
            reasonForSelection=decision.reason_for_selection,
            dependsOn=depends_on or [],
            canRunInParallel=parallel,
            timeoutSeconds=decision.timeout_seconds,
            maxRetries=decision.max_retries,
            fallbackModel=decision.fallback_model,
            expectedOutputSchema=schema,
        )
