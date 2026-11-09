"""Known infrastructure skills and the aliases that count as the same skill."""

# Canonical term -> aliases that count as the same skill.
INFRA: dict[str, list[str]] = {
    "aws": ["aws", "amazon web services"],
    "ec2": ["ec2"],
    "s3": ["s3"],
    "iam": ["iam"],
    "vpc": ["vpc"],
    "rds": ["rds"],
    "eks": ["eks"],
    "ecs": ["ecs"],
    "lambda": ["lambda"],
    "cloudwatch": ["cloudwatch"],
    "azure": ["azure"],
    "bicep": ["bicep"],
    "gcp": ["gcp", "google cloud"],
    "terraform": ["terraform"],
    "ansible": ["ansible"],
    "cloudformation": ["cloudformation"],
    "docker": ["docker"],
    "docker compose": ["docker compose", "docker-compose"],
    "kubernetes": ["kubernetes", "k8s"],
    "helm": ["helm"],
    "argo cd": ["argo cd", "argocd"],
    "linux": ["linux"],
    "ubuntu": ["ubuntu"],
    "centos": ["centos", "rhel", "red hat"],
    "systemd": ["systemd"],
    "bash": ["bash", "shell scripting"],
    "python": ["python"],
    "go": ["golang"],
    "powershell": ["powershell"],
    "ci/cd": ["ci/cd", "cicd"],
    "github actions": ["github actions"],
    "gitlab ci": ["gitlab ci", "gitlab-ci"],
    "jenkins": ["jenkins"],
    "git": ["git"],
    "nginx": ["nginx"],
    "apache": ["apache"],
    "traefik": ["traefik"],
    "prometheus": ["prometheus"],
    "grafana": ["grafana"],
    "loki": ["loki"],
    "elk": ["elk", "elasticsearch", "kibana", "opensearch"],
    "postgresql": ["postgresql", "postgres"],
    "mysql": ["mysql"],
    "redis": ["redis"],
    "dns": ["dns"],
    "tls": ["tls", "ssl"],
    "vpn": ["vpn", "wireguard"],
    "firewall": ["ufw", "iptables", "firewall", "security groups"],
    "sonarqube": ["sonarqube"],
    "vagrant": ["vagrant"],
}


WEB: dict[str, list[str]] = {
    "php": ["php"],
    "wordpress": ["wordpress"],
    "woocommerce": ["woocommerce"],
    "laravel": ["laravel"],
    "symfony": ["symfony"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript"],
    "react": ["react", "react.js", "reactjs"],
    "next.js": ["next.js", "nextjs"],
    "vue": ["vue", "vue.js", "vuejs"],
    "node.js": ["node.js", "nodejs"],
    "jquery": ["jquery"],
    "html": ["html", "html5"],
    "css": ["css", "css3"],
    "scss": ["scss", "sass"],
    "tailwind": ["tailwind", "tailwindcss"],
    "gutenberg": ["gutenberg"],
    "webflow": ["webflow"],
    "figma": ["figma"],
    "mysql": ["mysql"],
    "rest api": ["rest api", "restful", "rest apis"],
    "git": ["git"],
    "docker": ["docker"],
}

# Vocabulary per profile, used when generating skills from a resume.
VOCABULARIES: dict[str, dict[str, list[str]]] = {"devops": INFRA, "web": WEB}

# Every known spelling, used when matching skills in vacancies.
VOCABULARY: dict[str, list[str]] = {**WEB, **INFRA}


def aliases(skill: str) -> list[str]:
    """All spellings to look for when matching `skill` in a vacancy."""
    return VOCABULARY.get(skill, [skill])
