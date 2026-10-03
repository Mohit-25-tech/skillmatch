"""Deterministic synthetic career dataset; companies and openings are illustrative."""

import random

SKILL_GROUPS = {
    "Languages": "Python|JavaScript|TypeScript|Java|C|C++|C#|Go|Rust|Ruby|PHP|Swift|Kotlin|Dart|Scala|R|MATLAB|Julia|Perl|Lua|Haskell|Elixir|Clojure|F#|Objective-C|Solidity|Bash|PowerShell|SQL|Assembly",
    "Frontend": "HTML|CSS|React|Vue|Angular|Svelte|Next.js|Nuxt|Astro|Remix|jQuery|Bootstrap|Tailwind CSS|Sass|Less|Webpack|Vite|Rollup|esbuild|Babel|Redux|Zustand|MobX|React Query|GraphQL|Web Components|PWA|Web Accessibility|Responsive Design|Three.js",
    "Backend": "Node.js|Express|FastAPI|Django|Flask|Spring Boot|Laravel|Ruby on Rails|ASP.NET|NestJS|Koa|Hapi|Gin|Fiber|Actix|Phoenix|REST APIs|gRPC|WebSockets|OAuth|JWT|Microservices|Event Sourcing|CQRS|Domain Driven Design|API Design|Celery|RabbitMQ|Kafka|Nginx",
    "Data": "PostgreSQL|MySQL|SQLite|MongoDB|Redis|Elasticsearch|DynamoDB|Cassandra|Neo4j|CouchDB|MariaDB|Oracle|SQL Server|Snowflake|BigQuery|Redshift|Databricks|Apache Spark|Hadoop|Airflow|dbt|Pandas|NumPy|Polars|Dask|ETL|Data Modeling|Data Warehousing|Data Governance|Data Quality",
    "AI & ML": "Machine Learning|Deep Learning|TensorFlow|PyTorch|Scikit-learn|Keras|XGBoost|LightGBM|CatBoost|spaCy|NLTK|Transformers|Computer Vision|Natural Language Processing|Reinforcement Learning|Recommendation Systems|Time Series|Feature Engineering|Model Deployment|MLOps|MLflow|Kubeflow|Hugging Face|LangChain|Vector Databases|Prompt Engineering|RAG|Model Evaluation|Statistics|A/B Testing",
    "Cloud & DevOps": "AWS|Azure|Google Cloud|Docker|Kubernetes|Terraform|Ansible|Pulumi|CloudFormation|Jenkins|GitHub Actions|GitLab CI|CircleCI|Argo CD|Helm|Prometheus|Grafana|Datadog|Linux|Unix|Networking|Load Balancing|Serverless|AWS Lambda|Cloud Security|SRE|Incident Response|Observability|CI/CD|Git",
    "Design": "Figma|Sketch|Adobe XD|Photoshop|Illustrator|InDesign|After Effects|Blender|Cinema 4D|Framer|Webflow|UI Design|UX Research|Interaction Design|Design Systems|Prototyping|Wireframing|Information Architecture|Usability Testing|User Interviews|Journey Mapping|Service Design|Visual Design|Typography|Color Theory|Motion Design|Design Thinking|Product Design|Content Design|Accessibility Audits",
    "Product & Business": "Product Management|Agile|Scrum|Kanban|Jira|Confluence|Notion|Roadmapping|Stakeholder Management|Market Research|Competitive Analysis|Business Analysis|Requirements Gathering|OKRs|KPIs|Product Analytics|Amplitude|Mixpanel|Google Analytics|Looker|Tableau|Power BI|Excel|Financial Modeling|Pricing Strategy|Go-to-Market|Growth Strategy|Customer Success|Salesforce|HubSpot",
    "Testing & Security": "Pytest|Jest|Vitest|Cypress|Playwright|Selenium|JUnit|Mocha|Chai|Testing Library|Test Automation|Unit Testing|Integration Testing|Load Testing|k6|JMeter|Postman|Insomnia|OWASP|Penetration Testing|Threat Modeling|Cryptography|Identity Management|Network Security|SOC 2|ISO 27001|GDPR|Security Auditing|SonarQube|SAST",
    "Professional": "Communication|Leadership|Teamwork|Problem Solving|Critical Thinking|Project Management|Time Management|Mentoring|Technical Writing|Public Speaking|Negotiation|Conflict Resolution|Adaptability|Collaboration|Remote Collaboration|Presentation Skills|Documentation|Code Review|System Design|Algorithms|Data Structures|Object Oriented Programming|Functional Programming|Distributed Systems|Performance Optimization|Debugging|Research|Decision Making|Strategic Planning|Customer Empathy",
}
SKILLS = [
    {"name": name, "category": category}
    for category, names in SKILL_GROUPS.items()
    for name in names.split("|")
]
PROFILES = [
    ("Senior Frontend Developer", ["React", "TypeScript", "JavaScript", "CSS", "Next.js", "Git"]),
    ("Full Stack Engineer", ["React", "Node.js", "TypeScript", "PostgreSQL", "Docker", "REST APIs"]),
    ("Product Designer", ["Figma", "UI Design", "UX Research", "Prototyping", "Design Systems"]),
    ("Python Backend Engineer", ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "Pytest"]),
    ("Data Scientist", ["Python", "Pandas", "Machine Learning", "SQL", "Statistics", "Scikit-learn"]),
    ("Machine Learning Engineer", ["Python", "PyTorch", "MLOps", "Docker", "Transformers", "AWS"]),
    ("DevOps Engineer", ["AWS", "Kubernetes", "Terraform", "CI/CD", "Linux", "Docker"]),
    ("Mobile Developer", ["Swift", "Kotlin", "Git", "REST APIs", "Unit Testing"]),
    ("Analytics Engineer", ["SQL", "dbt", "Snowflake", "Python", "Data Modeling"]),
    ("Security Engineer", ["Cloud Security", "Python", "OWASP", "Threat Modeling", "Linux"]),
]
COMPANIES = [
    "Linear",
    "Vercel",
    "Notion",
    "Stripe",
    "Figma",
    "Supabase",
    "Ramp",
    "Arc",
    "Mercury",
    "Raycast",
    "Loom",
    "Webflow",
    "Retool",
    "Resend",
    "Cal.com",
    "Clerk",
    "Neon",
    "PlanetScale",
    "PostHog",
    "Tailscale",
]


def generate_jobs() -> list[dict]:
    rng = random.Random(42)
    jobs = []
    for i in range(200):
        title, skills = PROFILES[i % len(PROFILES)]
        company = COMPANIES[i % len(COMPANIES)]
        minimum = rng.randrange(85, 160, 5) * 1000
        jobs.append(
            {
                "title": title,
                "company": company,
                "location": ["Remote", "San Francisco, CA", "New York, NY", "London, UK", "Bengaluru, IN"][
                    i % 5
                ],
                "employment_type": "Contract" if i % 9 == 0 else "Full-time",
                "salary_min": minimum,
                "salary_max": minimum + 40000,
                "description": f"Join the {company} team as a {title.lower()} and help build thoughtful products people love. You will own projects from idea to release, collaborate with design and engineering, and make decisions supported by user research and reliable data. We value clear communication, accessible experiences, and pragmatic problem solving. Bring practical experience with {', '.join(skills)}. Benefits include flexible working, a learning budget, and generous paid time off. This is a synthetic opening for the SkillMatch demonstration.",
                "skills": skills,
            }
        )
    return jobs
