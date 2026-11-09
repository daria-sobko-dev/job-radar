from jobradar.sources import dou, greenhouse, lever


def test_dou_parses_title_company_location(dou_xml):
    jobs = dou.parse(dou_xml)
    assert len(jobs) == 3
    first = jobs[0]
    assert first.title == "Junior DevOps Engineer"
    assert first.company == "Acme Cloud"
    assert first.location == "Київ, віддалено"
    assert first.id == "400001"
    assert first.key == "dou:400001"


def test_dou_description_is_plain_text(dou_xml):
    desc = dou.parse(dou_xml)[0].description
    assert "<" not in desc
    assert "AWS" in desc and "GitHub Actions" in desc


def test_dou_title_without_company_is_kept_whole():
    xml = "<rss><channel><item><title>DevOps role</title><link>https://jobs.dou.ua/x/</link></item></channel></rss>"
    job = dou.parse(xml)[0]
    assert job.title == "DevOps role"
    assert job.company == ""


def test_greenhouse_unescapes_content(greenhouse_data):
    jobs = greenhouse.parse(greenhouse_data, "DKB Code Factory")
    assert jobs[0].location == "Valencia, Spain"
    assert jobs[0].company == "DKB Code Factory"
    assert "Terraform" in jobs[0].description
    assert "&lt;" not in jobs[0].description and "<p>" not in jobs[0].description


def test_lever_joins_lists_and_converts_date(lever_data):
    job = lever.parse(lever_data, "Example")[0]
    assert job.title == "Cloud Engineer"
    assert job.location == "Remote - Europe"
    assert "Terraform" in job.description
    assert job.published.startswith("2025-11-09")
