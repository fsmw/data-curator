"""
Agent Orchestrator for Mises Data Curator.

Coordinates multiple agents to perform complex multi-step analyses.
Inspired by Data Formulator's agentic workflow patterns.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd

from .base import BaseAgent, AgentResponse, TableContext, create_table_context
from .client import MisesLLMClient, get_default_client
from .transform import DataTransformAgent, SQLTransformAgent
from .exploration import ExplorationAgent, DataQualityAgent
from .clean import DataCleanAgent
from .report import ReportGenAgent

logger = logging.getLogger(__name__)


# =============================================================================
# Workflow Types
# =============================================================================

class WorkflowStep(Enum):
    """Types of workflow steps."""
    CLEAN = "clean"
    TRANSFORM = "transform"
    EXPLORE = "explore"
    REPORT = "report"
    CUSTOM = "custom"


@dataclass
class StepResult:
    """Result of a single workflow step."""
    step_name: str
    step_type: WorkflowStep
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    output_data: Optional[pd.DataFrame] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class WorkflowResult:
    """Complete workflow execution result."""
    workflow_name: str
    success: bool
    steps: List[StepResult] = field(default_factory=list)
    final_data: Optional[pd.DataFrame] = None
    final_report: Optional[str] = None
    
    def get_step(self, name: str) -> Optional[StepResult]:
        """Get a specific step by name."""
        for step in self.steps:
            if step.step_name == name:
                return step
        return None


# =============================================================================
# Agent Orchestrator
# =============================================================================

class AgentOrchestrator:
    """
    Orchestrates multiple agents for complex data workflows.
    
    Provides high-level methods for common data analysis patterns
    and custom workflow definition.
    """

    def __init__(
        self,
        client: Optional[MisesLLMClient] = None,
        language: str = "es"
    ):
        """
        Initialize the orchestrator.
        
        Args:
            client: Shared LLM client for all agents
            language: Output language
        """
        self.client = client or get_default_client()
        self.language = language
        
        # Initialize agents lazily
        self._transform_agent: Optional[DataTransformAgent] = None
        self._sql_agent: Optional[SQLTransformAgent] = None
        self._explore_agent: Optional[ExplorationAgent] = None
        self._clean_agent: Optional[DataCleanAgent] = None
        self._report_agent: Optional[ReportGenAgent] = None
        self._quality_agent: Optional[DataQualityAgent] = None

    # =========================================================================
    # Lazy Agent Initialization
    # =========================================================================

    @property
    def transform_agent(self) -> DataTransformAgent:
        if self._transform_agent is None:
            self._transform_agent = DataTransformAgent(
                client=self.client, language=self.language
            )
        return self._transform_agent

    @property
    def sql_agent(self) -> SQLTransformAgent:
        if self._sql_agent is None:
            self._sql_agent = SQLTransformAgent(
                client=self.client, language=self.language
            )
        return self._sql_agent

    @property
    def explore_agent(self) -> ExplorationAgent:
        if self._explore_agent is None:
            self._explore_agent = ExplorationAgent(
                client=self.client, language=self.language
            )
        return self._explore_agent

    @property
    def clean_agent(self) -> DataCleanAgent:
        if self._clean_agent is None:
            self._clean_agent = DataCleanAgent(
                client=self.client, language=self.language
            )
        return self._clean_agent

    @property
    def report_agent(self) -> ReportGenAgent:
        if self._report_agent is None:
            self._report_agent = ReportGenAgent(
                client=self.client, language=self.language
            )
        return self._report_agent

    @property
    def quality_agent(self) -> DataQualityAgent:
        if self._quality_agent is None:
            self._quality_agent = DataQualityAgent(
                client=self.client, language=self.language
            )
        return self._quality_agent

    # =========================================================================
    # Common Workflows
    # =========================================================================

    def analyze_dataset(
        self,
        df: pd.DataFrame,
        name: str = "datos",
        description: str = "",
        clean_data: bool = True,
        generate_report: bool = True
    ) -> WorkflowResult:
        """
        Complete dataset analysis workflow.
        
        Steps:
        1. Quality check
        2. Clean data (optional)
        3. Generate exploration suggestions
        4. Generate report (optional)
        
        Args:
            df: Input DataFrame
            name: Dataset name
            description: Dataset description
            clean_data: Whether to auto-clean issues
            generate_report: Whether to generate narrative report
            
        Returns:
            WorkflowResult with all step results
        """
        workflow = WorkflowResult(workflow_name="analyze_dataset", success=True)
        current_df = df.copy()
        
        # Step 1: Quality Check
        logger.info("Step 1: Quality check")
        try:
            quality_report = self.clean_agent.analyze_quality_fast(current_df, name)
            workflow.steps.append(StepResult(
                step_name="quality_check",
                step_type=WorkflowStep.CLEAN,
                success=True,
                result=quality_report.to_dict(),
                metadata={"issues_found": len(quality_report.issues)}
            ))
        except Exception as e:
            workflow.steps.append(StepResult(
                step_name="quality_check",
                step_type=WorkflowStep.CLEAN,
                success=False,
                error=str(e)
            ))
        
        # Step 2: Clean Data (if requested and issues found)
        if clean_data and workflow.steps[-1].success:
            quality_result = workflow.steps[-1].result
            if quality_result and quality_result.get("issues"):
                logger.info("Step 2: Cleaning data")
                try:
                    # Apply automatic cleaning
                    current_df = self.clean_agent.clean_nulls(current_df, strategy="auto")
                    current_df = self.clean_agent.remove_duplicates(current_df)
                    
                    workflow.steps.append(StepResult(
                        step_name="data_cleaning",
                        step_type=WorkflowStep.CLEAN,
                        success=True,
                        output_data=current_df,
                        metadata={"rows_after": len(current_df)}
                    ))
                except Exception as e:
                    workflow.steps.append(StepResult(
                        step_name="data_cleaning",
                        step_type=WorkflowStep.CLEAN,
                        success=False,
                        error=str(e)
                    ))
        
        # Step 3: Exploration suggestions
        logger.info("Step 3: Generating exploration suggestions")
        try:
            table_ctx = create_table_context(current_df, name, description)
            suggestions = self.explore_agent.get_suggestions_list([table_ctx])
            workflow.steps.append(StepResult(
                step_name="exploration",
                step_type=WorkflowStep.EXPLORE,
                success=True,
                result=suggestions,
                metadata={"suggestions_count": len(suggestions)}
            ))
        except Exception as e:
            workflow.steps.append(StepResult(
                step_name="exploration",
                step_type=WorkflowStep.EXPLORE,
                success=False,
                error=str(e)
            ))
        
        # Step 4: Generate Report (if requested)
        if generate_report:
            logger.info("Step 4: Generating report")
            try:
                report = self.report_agent.generate_quick_report(
                    current_df, name, f"Análisis de {name}"
                )
                workflow.steps.append(StepResult(
                    step_name="report",
                    step_type=WorkflowStep.REPORT,
                    success=True,
                    result=report.to_dict(),
                    metadata={"findings_count": len(report.hallazgos)}
                ))
                workflow.final_report = report.to_markdown()
            except Exception as e:
                workflow.steps.append(StepResult(
                    step_name="report",
                    step_type=WorkflowStep.REPORT,
                    success=False,
                    error=str(e)
                ))
        
        workflow.final_data = current_df
        workflow.success = all(s.success for s in workflow.steps)
        
        return workflow

    def transform_and_analyze(
        self,
        df: pd.DataFrame,
        goal: str,
        name: str = "datos",
        use_sql: bool = False
    ) -> WorkflowResult:
        """
        Transform data according to goal, then analyze results.
        
        Steps:
        1. Transform data (Python or SQL)
        2. Analyze transformed data
        
        Args:
            df: Input DataFrame
            goal: Transformation goal in natural language
            name: Dataset name
            use_sql: Use SQL instead of Python
            
        Returns:
            WorkflowResult with transformation and analysis
        """
        workflow = WorkflowResult(workflow_name="transform_and_analyze", success=True)
        
        # Step 1: Transform
        logger.info(f"Step 1: Transform ({'SQL' if use_sql else 'Python'})")
        try:
            table_ctx = create_table_context(df, name)
            agent = self.sql_agent if use_sql else self.transform_agent
            
            response = agent.transform(goal, [table_ctx], execute=True)
            
            if response.status == "ok" and response.result_data is not None:
                workflow.steps.append(StepResult(
                    step_name="transform",
                    step_type=WorkflowStep.TRANSFORM,
                    success=True,
                    result={"code": response.code},
                    output_data=response.result_data,
                    metadata={"rows_output": len(response.result_data)}
                ))
                current_df = response.result_data
            else:
                workflow.steps.append(StepResult(
                    step_name="transform",
                    step_type=WorkflowStep.TRANSFORM,
                    success=False,
                    error=response.error or "Transform failed",
                    result={"code": response.code}
                ))
                workflow.success = False
                return workflow
                
        except Exception as e:
            workflow.steps.append(StepResult(
                step_name="transform",
                step_type=WorkflowStep.TRANSFORM,
                success=False,
                error=str(e)
            ))
            workflow.success = False
            return workflow
        
        # Step 2: Analyze result
        logger.info("Step 2: Analyzing transformed data")
        try:
            report = self.report_agent.generate_quick_report(
                current_df, name, f"Análisis: {goal[:50]}"
            )
            workflow.steps.append(StepResult(
                step_name="analysis",
                step_type=WorkflowStep.REPORT,
                success=True,
                result=report.to_dict()
            ))
            workflow.final_report = report.to_markdown()
        except Exception as e:
            workflow.steps.append(StepResult(
                step_name="analysis",
                step_type=WorkflowStep.REPORT,
                success=False,
                error=str(e)
            ))
        
        workflow.final_data = current_df
        workflow.success = all(s.success for s in workflow.steps)
        
        return workflow

    # =========================================================================
    # Custom Workflow Execution
    # =========================================================================

    def run_workflow(
        self,
        df: pd.DataFrame,
        steps: List[Dict[str, Any]],
        name: str = "datos"
    ) -> WorkflowResult:
        """
        Run a custom workflow defined by a list of steps.
        
        Each step is a dict with:
        - type: 'clean', 'transform', 'explore', 'report'
        - config: Configuration for the step
        
        Args:
            df: Input DataFrame
            steps: List of step definitions
            name: Dataset name
            
        Returns:
            WorkflowResult
        """
        workflow = WorkflowResult(workflow_name="custom", success=True)
        current_df = df.copy()
        
        for i, step_def in enumerate(steps):
            step_type = step_def.get("type", "").lower()
            config = step_def.get("config", {})
            step_name = step_def.get("name", f"step_{i+1}")
            
            logger.info(f"Running step {i+1}: {step_name} ({step_type})")
            
            try:
                if step_type == "clean":
                    strategy = config.get("strategy", "auto")
                    current_df = self.clean_agent.clean_nulls(current_df, strategy)
                    current_df = self.clean_agent.remove_duplicates(current_df)
                    
                    workflow.steps.append(StepResult(
                        step_name=step_name,
                        step_type=WorkflowStep.CLEAN,
                        success=True,
                        output_data=current_df
                    ))
                    
                elif step_type == "transform":
                    goal = config.get("goal", "")
                    use_sql = config.get("sql", False)
                    
                    table_ctx = create_table_context(current_df, name)
                    agent = self.sql_agent if use_sql else self.transform_agent
                    
                    response = agent.transform(goal, [table_ctx], execute=True)
                    
                    if response.status == "ok" and response.result_data is not None:
                        current_df = response.result_data
                        workflow.steps.append(StepResult(
                            step_name=step_name,
                            step_type=WorkflowStep.TRANSFORM,
                            success=True,
                            result={"code": response.code},
                            output_data=current_df
                        ))
                    else:
                        workflow.steps.append(StepResult(
                            step_name=step_name,
                            step_type=WorkflowStep.TRANSFORM,
                            success=False,
                            error=response.error
                        ))
                        
                elif step_type == "explore":
                    table_ctx = create_table_context(current_df, name)
                    suggestions = self.explore_agent.get_suggestions_list([table_ctx])
                    
                    workflow.steps.append(StepResult(
                        step_name=step_name,
                        step_type=WorkflowStep.EXPLORE,
                        success=True,
                        result=suggestions
                    ))
                    
                elif step_type == "report":
                    topic = config.get("topic", f"Análisis de {name}")
                    report = self.report_agent.generate_quick_report(
                        current_df, name, topic
                    )
                    
                    workflow.steps.append(StepResult(
                        step_name=step_name,
                        step_type=WorkflowStep.REPORT,
                        success=True,
                        result=report.to_dict()
                    ))
                    workflow.final_report = report.to_markdown()
                    
                else:
                    workflow.steps.append(StepResult(
                        step_name=step_name,
                        step_type=WorkflowStep.CUSTOM,
                        success=False,
                        error=f"Unknown step type: {step_type}"
                    ))
                    
            except Exception as e:
                workflow.steps.append(StepResult(
                    step_name=step_name,
                    step_type=WorkflowStep.CUSTOM,
                    success=False,
                    error=str(e)
                ))
        
        workflow.final_data = current_df
        workflow.success = all(s.success for s in workflow.steps)
        
        return workflow


# =============================================================================
# Convenience Functions
# =============================================================================

def analyze(df: pd.DataFrame, name: str = "datos") -> WorkflowResult:
    """
    Quick analysis of a DataFrame.
    
    Args:
        df: DataFrame to analyze
        name: Dataset name
        
    Returns:
        WorkflowResult with complete analysis
    """
    orchestrator = AgentOrchestrator()
    return orchestrator.analyze_dataset(df, name)


def transform(df: pd.DataFrame, goal: str, name: str = "datos") -> WorkflowResult:
    """
    Transform a DataFrame according to a natural language goal.
    
    Args:
        df: DataFrame to transform
        goal: Transformation goal
        name: Dataset name
        
    Returns:
        WorkflowResult with transformed data
    """
    orchestrator = AgentOrchestrator()
    return orchestrator.transform_and_analyze(df, goal, name)
