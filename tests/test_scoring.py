from jobradar.models import Job
from jobradar.scoring import rank, rejection_reason, score
from jobradar.sources import dou, greenhouse
from jobradar.text import contains


def make_job(title, location="Remote", description="", company="X"):
    return Job(
        source="t",
        id=title,
        title=title,
        company=company,
        location=location,
        url=f"https://example.com/{title}",
        description=description,
    )


def test_term_matching_respects_word_boundaries():
    assert contains("we use aws daily", "aws")
    assert not contains("laws and rules", "aws")
    assert not contains("github actions", "git")
    assert contains("strong ci/cd skills", "ci/cd")
    assert contains("київ, віддалено", "віддалено")


def test_junior_remote_devops_matches(dou_xml, profile):
    job = dou.parse(dou_xml)[0]
    match = score(job, profile)
    assert match is not None
    assert "aws" in match.skills and "terraform" in match.skills
    assert any(n.startswith("junior") for n in match.notes)


def test_senior_title_is_rejected(dou_xml, profile):
    job = dou.parse(dou_xml)[1]
    assert "excluded" in rejection_reason(job, profile)
    assert score(job, profile) is None


def test_office_only_in_other_city_is_rejected(dou_xml, profile):
    job = dou.parse(dou_xml)[2]
    assert "location" in rejection_reason(job, profile)


def test_valencia_greenhouse_job_matches_and_manager_does_not(greenhouse_data, profile):
    jobs = greenhouse.parse(greenhouse_data, "DKB Code Factory")
    matches = rank(jobs, profile)
    assert [m.job.title for m in matches] == ["DevOps Engineer - Credit Cards"]


def test_irrelevant_title_is_rejected(profile):
    job = make_job("Frontend Developer", description="AWS Terraform Docker Linux")
    assert "target role" in rejection_reason(job, profile)


def test_penalties_can_push_below_threshold(profile):
    weak = make_job("DevOps Engineer", description="Bash. 5+ years required. 24/7 support.")
    assert score(weak, profile) is None


def test_rank_sorts_by_score(profile):
    strong = make_job("Junior DevOps Engineer", description="AWS Terraform Linux Docker Kubernetes")
    ok = make_job("Cloud Engineer", description="AWS Terraform")
    ranked = rank([ok, strong], profile)
    assert [m.job.title for m in ranked] == ["Junior DevOps Engineer", "Cloud Engineer"]


def test_red_flag_industry_is_rejected(profile):
    job = make_job(
        "Junior DevOps Engineer",
        description="AWS, Terraform, Linux, Docker. We build live dealer games for the iGaming market.",
        company="ICONIC21",
    )
    assert rejection_reason(job, profile) == "red flag: igaming"
    assert score(job, profile) is None


def test_red_flag_in_ukrainian_is_rejected(profile):
    job = make_job("DevOps Engineer", description="AWS Terraform Linux. Продукт: онлайн-казино.")
    assert "казино" in rejection_reason(job, profile)


def test_similar_words_are_not_red_flags(profile):
    job = make_job("DevOps Engineer", description="AWS Terraform Linux Docker. Gaming studio, game servers.")
    assert rejection_reason(job, profile) is None
