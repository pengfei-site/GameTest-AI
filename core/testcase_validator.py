
from core.case_schemas import (
    TestCaseCandidateCollection,
    TestCaseValidationReport,
)


def validate_testcases(
    result: TestCaseCandidateCollection,
) -> TestCaseValidationReport:
    """
    Python 测试用例质量检查。

    检查范围：
    1. 用例标题不能为空或纯空白
    2. 测试目的不能为空或纯空白
    3. 测试步骤序号必须从 1 开始连续递增
    4. 测试操作不能为空或纯空白
    5. 预期结果不能为空或纯空白
    6. 前置条件、后置条件不能包含纯空白条目
    7. 同一用例中完全重复的步骤
    8. 同一批次中完全重复的候选用例
    9. 候选用例数量为 0

    ERROR 会导致校验不通过。
    WARNING 不影响校验通过状态。
    """

    errors = []
    warnings = []

    candidates = result.candidates

    # --------------------------------------------------
    # V09：候选用例数量检查
    # --------------------------------------------------

    if len(candidates) == 0:
        warnings.append("当前没有生成任何候选用例。")

    # --------------------------------------------------
    # V01～V07：逐条检查候选用例
    # --------------------------------------------------

    for case_index, candidate in enumerate(candidates, start=1):

        case_label = f"第 {case_index} 条候选用例"

        # V01：标题不能为空或纯空白
        if not candidate.title.strip():
            errors.append(
                f"{case_label}：测试用例标题不能为空或纯空白。"
            )

        # V02：测试目的不能为空或纯空白
        if not candidate.objective.strip():
            errors.append(
                f"{case_label}：测试目的不能为空或纯空白。"
            )

        # V03：步骤序号必须从 1 开始连续递增
        for expected_no, step in enumerate(
            candidate.steps,
            start=1,
        ):
            if step.step_no != expected_no:
                errors.append(
                    f"{case_label}：步骤序号不连续，"
                    f"预期为 {expected_no}，"
                    f"实际为 {step.step_no}。"
                )

        # V04、V05：检查步骤操作和预期结果
        for step_index, step in enumerate(
            candidate.steps,
            start=1,
        ):

            if not step.action.strip():
                errors.append(
                    f"{case_label}：第 {step_index} 步的"
                    "测试操作不能为空或纯空白。"
                )

            if not step.expected_result.strip():
                errors.append(
                    f"{case_label}：第 {step_index} 步的"
                    "预期结果不能为空或纯空白。"
                )

        # V06：检查前置条件
        for condition_index, condition in enumerate(
            candidate.preconditions,
            start=1,
        ):
            if not condition.strip():
                errors.append(
                    f"{case_label}：第 {condition_index} 条"
                    "前置条件不能为空或纯空白。"
                )

        # V06：检查后置条件
        for condition_index, condition in enumerate(
            candidate.postconditions,
            start=1,
        ):
            if not condition.strip():
                errors.append(
                    f"{case_label}：第 {condition_index} 条"
                    "后置条件不能为空或纯空白。"
                )

        # V07：检查同一用例内完全重复的步骤
        seen_steps = set()

        for step_index, step in enumerate(
            candidate.steps,
            start=1,
        ):
            step_signature = (
                step.action.strip(),
                step.expected_result.strip(),
            )

            if step_signature in seen_steps:
                warnings.append(
                    f"{case_label}：第 {step_index} 步"
                    "与前面的步骤完全重复。"
                )
            else:
                seen_steps.add(step_signature)

    # --------------------------------------------------
    # V08：检查同一批次中完全重复的候选用例
    # --------------------------------------------------

    seen_cases = {}

    for case_index, candidate in enumerate(candidates, start=1):

        case_signature = (
            candidate.title.strip(),
            candidate.objective.strip(),
            candidate.priority,
            tuple(
                condition.strip()
                for condition in candidate.preconditions
            ),
            tuple(
                (
                    step.step_no,
                    step.action.strip(),
                    step.expected_result.strip(),
                )
                for step in candidate.steps
            ),
            tuple(
                condition.strip()
                for condition in candidate.postconditions
            ),
        )

        if case_signature in seen_cases:
            first_index = seen_cases[case_signature]

            warnings.append(
                f"第 {case_index} 条候选用例与"
                f"第 {first_index} 条候选用例完全重复。"
            )
        else:
            seen_cases[case_signature] = case_index

    # --------------------------------------------------
    # 生成校验报告
    # --------------------------------------------------

    return TestCaseValidationReport(
        passed=len(errors) == 0,
        total=len(candidates),
        error_count=len(errors),
        warning_count=len(warnings),
        errors=errors,
        warnings=warnings,
    )
