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


def test_fancy_unicode_title_is_normalised(profile):
    job = make_job("𝗦𝗲𝗻𝗶𝗼𝗿 𝗗𝗲𝘃𝗢𝗽𝘀 𝗘𝗻𝗴𝗶𝗻𝗲𝗲𝗿", description="AWS Terraform")
    assert rejection_reason(job, profile) == "title excluded: senior"


def test_work_from_abroad_is_allowed_and_ranked_higher(profile):
    abroad = make_job("DevOps Engineer", location="за кордоном, віддалено", description="AWS Terraform Linux")
    ukraine = make_job("Cloud Engineer", location="Київ, віддалено", description="AWS Terraform Linux")
    ranked = rank([ukraine, abroad], profile)
    assert ranked[0].job.title == "DevOps Engineer"
    assert "за кордоном +4" in ranked[0].notes


def test_valencia_gets_location_bonus(profile):
    match = score(make_job("DevOps Engineer", location="Valencia, Spain", description="AWS Terraform"), profile)
    assert "valencia +5" in match.notes and "spain +5" in match.notes


def test_web_server_administrator_is_a_target_role(profile):
    job = make_job("Web Server Administrator", location="за кордоном, віддалено", description="Linux Nginx Bash")
    assert rejection_reason(job, profile) is None


def test_wordpress_job_goes_to_web_profile(profiles):
    job = make_job(
        "Junior WordPress Developer", location="за кордоном, віддалено", description="PHP, WordPress, WooCommerce, JS"
    )
    match = rank([job], profiles)[0]
    assert match.profile == "web"
    assert {"php", "wordpress", "woocommerce", "javascript"} <= set(match.skills)


def test_devops_job_goes_to_devops_profile(profiles):
    job = make_job("Junior DevOps Engineer", description="AWS Terraform Linux Docker")
    assert rank([job], profiles)[0].profile == "devops"


def test_fullstack_laravel_title_is_web(web_profile):
    job = make_job("Middle Fullstack Developer (Laravel + Vue)", description="PHP Laravel Vue.js MySQL REST API")
    match = score(job, web_profile)
    assert match is not None and "laravel" in match.skills and "vue" in match.skills


def test_shared_filters_apply_to_every_profile(web_profile):
    job = make_job("PHP Developer", description="PHP WordPress for an online casino")
    assert "red flag: casino" == rejection_reason(job, web_profile)


def test_senior_web_title_is_excluded(web_profile):
    assert "excluded" in rejection_reason(make_job("Senior Frontend Developer"), web_profile)
