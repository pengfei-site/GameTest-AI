from core.testcase_manual_review_service import (
    approve_candidate,
)

CANDIDATE_ID = "f5656d37-6a53-4f69-85a0-adf4994908ca"


def main():
    result = approve_candidate(
        candidate_id=CANDIDATE_ID,
        comment=(
            "人工审核通过：用例内容与来源测试点及需求规则一致，"
            "步骤和预期结果清晰，满足 MVP-1 用例质量要求。"
        ),
    )

    print("=" * 60)
    print("人工审核结果")
    print("=" * 60)
    print(result)


if __name__ == "__main__":
    main()