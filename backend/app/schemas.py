from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class Register(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    role: Literal["candidate", "recruiter"] = "candidate"

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if len(value.strip()) < 2:
            raise ValueError("Enter your name")
        return value.strip()


class Login(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class JobInput(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    company: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=2, max_length=100)
    employment_type: Literal["Full-time", "Part-time", "Contract", "Internship"] = "Full-time"
    description: str = Field(min_length=40, max_length=20000)
    salary_min: int | None = Field(default=None, ge=0, le=10000000)
    salary_max: int | None = Field(default=None, ge=0, le=10000000)
    salary_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    salary_interval: Literal["hour", "month", "year"] | None = None
    remote: bool = False
    skills: list[str] = Field(min_length=1, max_length=30)

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, values: list[str]) -> list[str]:
        values = list(dict.fromkeys(v.strip() for v in values))
        if any(not v or len(v) > 100 for v in values):
            raise ValueError("Skills must contain 1–100 characters")
        return values

    @model_validator(mode="after")
    def salary_order(self):
        if self.salary_max is not None and self.salary_min is not None and self.salary_max < self.salary_min:
            raise ValueError("Maximum salary must be at least minimum salary")
        return self


class MatchInput(BaseModel):
    resume_id: int
    job_id: int


class StatusInput(BaseModel):
    status: Literal["Applied", "Reviewing", "Interview", "Offer", "Rejected", "Hired"]


class UserUpdate(BaseModel):
    active: bool
