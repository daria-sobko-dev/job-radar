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
profile:
  min_score: 1
  # keep this comment
  # BEGIN skills
  skills:
    old: 1
  # END skills

  title_bonus:
    junior: 3
"""


def test_counts_known_skills_and_ignores_others():
    counts = resume.count_skills(RESUME)
    assert counts["aws"] == 3  # "laws"/"lawyers" must not count
    assert counts["terraform"] == 2
    assert "react" not in counts  # not an infrastructure skill


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
    assert data["profile"]["skills"]["aws"] == 2
    assert data["profile"]["skills"]["ci/cd"] == 1
    assert data["profile"]["title_bonus"] == {"junior": 3}


def test_missing_markers_is_an_error():
    with pytest.raises(ValueError):
        resume.replace_block("profile:\n  skills: {}\n", "block")


def test_scoring_matches_skill_aliases():
    profile = Profile.from_config({"min_score": 1, "title_keywords": ["devops"], "skills": {"kubernetes": 1}})
    job = Job("t", "1", "DevOps Engineer", "X", "Remote", "https://x", description="We run k8s.")
    match = score(job, profile)
    assert match is not None and match.skills == ["kubernetes"]
