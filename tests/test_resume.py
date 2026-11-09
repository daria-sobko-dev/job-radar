import pytest
import yaml

from jobradar import resume
from jobradar.models import Job
from jobradar.scoring import Profile, score

RESUME = """
Junior DevOps Engineer. AWS (EC2, S3), Terraform, Docker, Kubernetes basics.
Built CI/CD with GitHub Actions; AWS and Docker daily. Terraform modules for AWS.
Also wrote React apps and talked to lawyers about laws.
"""

CONFIG = """\
profiles:
  devops:
    min_score: 1
    # keep this comment
    # BEGIN skills devops
    skills:
      old: 1
    # END skills devops

    title_bonus:
      junior: 3
  web:
    # BEGIN skills web
    skills:
      php: 2
    # END skills web
"""


def test_counts_known_skills_and_ignores_others():
    counts = resume.count_skills(RESUME)
    assert counts["aws"] == 3  # "laws"/"lawyers" must not count
    assert counts["terraform"] == 2
    assert "react" not in counts  # not an infrastructure skill: devops vocabulary only


def test_core_skills_get_higher_weight():
    weights = resume.to_weights({"aws": 5, "helm": 1})
    assert weights == {"aws": resume.CORE_WEIGHT, "helm": resume.BASE_WEIGHT}
    assert list(weights) == ["aws", "helm"]


def test_write_replaces_only_the_marked_block(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(CONFIG, encoding="utf-8")
    src = tmp_path / "cv.txt"
    src.write_text(RESUME, encoding="utf-8")

    assert resume.main([str(src), "--config", str(cfg), "--write"]) == 0
    text = cfg.read_text(encoding="utf-8")
    assert "# keep this comment" in text
    assert "old: 1" not in text
    data = yaml.safe_load(text)
    assert data["profiles"]["devops"]["skills"]["aws"] == 2
    assert data["profiles"]["devops"]["skills"]["ci/cd"] == 1
    assert data["profiles"]["devops"]["title_bonus"] == {"junior": 3}
    assert data["profiles"]["web"]["skills"] == {"php": 2}  # other profile untouched


def test_missing_markers_is_an_error():
    with pytest.raises(ValueError):
        resume.replace_block("profile:\n  skills: {}\n", {"aws": 1}, "cv.txt", "devops")


def test_scoring_matches_skill_aliases():
    profile = Profile.from_config({"min_score": 1, "title_keywords": ["devops"], "skills": {"kubernetes": 1}})
    job = Job("t", "1", "DevOps Engineer", "X", "Remote", "https://x", description="We run k8s.")
    match = score(job, profile)
    assert match is not None and match.skills == ["kubernetes"]


def test_web_profile_uses_web_vocabulary(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(CONFIG, encoding="utf-8")
    src = tmp_path / "cv.txt"
    src.write_text("WordPress and PHP sites, React, WordPress blocks, PHP, PHP. AWS too.", encoding="utf-8")

    assert resume.main([str(src), "--config", str(cfg), "--profile", "web", "--write"]) == 0
    data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    assert data["profiles"]["web"]["skills"] == {"php": 2, "react": 1, "wordpress": 1}
    assert data["profiles"]["devops"]["skills"] == {"old": 1}
