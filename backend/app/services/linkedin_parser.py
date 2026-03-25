"""
Complete LinkedIn profile parser to extract all profile information.
Handles JSON exports, PDF, and DOCX formats.
"""
import json
import re
from typing import Any


class LinkedInProfileParser:
    """Parse LinkedIn profile data from various formats into structured data."""
    
    @staticmethod
    def parse_json_profile(data: dict[str, Any]) -> dict[str, Any]:
        """Parse LinkedIn JSON export format."""
        profile_info = {}
        
        # Personal Info from profile section
        if "profile" in data:
            profile = data["profile"][0] if isinstance(data["profile"], list) else data["profile"]
            profile_info["full_name"] = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()
            profile_info["headline"] = profile.get("headline", "")
            profile_info["about"] = profile.get("summary", "")
            
            # Location
            if "locationName" in profile:
                profile_info["location"] = profile["locationName"]
        
        # Skills
        skills = []
        if "skills" in data:
            skills_data = data["skills"][0] if isinstance(data["skills"], list) else data["skills"]
            for skill_entry in skills_data.get("skillName", []):
                if isinstance(skill_entry, dict):
                    skills.append(skill_entry.get("name", ""))
                else:
                    skills.append(str(skill_entry))
        profile_info["skills"] = skills
        
        # Experience
        experience = []
        if "experience" in data:
            exp_data = data["experience"][0] if isinstance(data["experience"], list) else data["experience"]
            for job in exp_data.get("jobTitle", []) if isinstance(exp_data.get("jobTitle"), list) else []:
                if isinstance(job, dict):
                    experience.append({
                        "title": job.get("title", ""),
                        "company": job.get("company", ""),
                        "start_date": job.get("startDate", ""),
                        "end_date": job.get("endDate", ""),
                        "description": job.get("description", ""),
                        "location": job.get("location", ""),
                    })
        
        # Extract current position
        if experience:
            profile_info["current_position"] = experience[0].get("title", "")
            profile_info["current_company"] = experience[0].get("company", "")
            profile_info["years_of_experience"] = len(experience)
        else:
            profile_info["current_position"] = ""
            profile_info["current_company"] = ""
            profile_info["years_of_experience"] = 0
        
        profile_info["work_history"] = experience
        
        # Education
        education = []
        if "education" in data:
            edu_data = data["education"][0] if isinstance(data["education"], list) else data["education"]
            for edu in edu_data.get("schoolName", []) if isinstance(edu_data.get("schoolName"), list) else []:
                if isinstance(edu, dict):
                    education.append({
                        "school": edu.get("schoolName", ""),
                        "degree": edu.get("fieldOfStudy", ""),
                        "start_date": edu.get("startDate", ""),
                        "end_date": edu.get("endDate", ""),
                    })
        profile_info["education"] = education
        
        return profile_info
    
    @staticmethod
    def parse_text_profile(text: str) -> dict[str, Any]:
        """Parse LinkedIn profile from PDF/DOCX extracted text."""
        profile_info = {
            "full_name": "",
            "headline": "",
            "about": "",
            "location": "",
            "skills": [],
            "current_position": "",
            "current_company": "",
            "years_of_experience": 0,
            "work_history": [],
            "education": [],
        }
        
        lines = text.split("\n")
        
        # Extract name (usually first non-empty line)
        for line in lines:
            line = line.strip()
            if line and len(line.split()) <= 4:  # Assume name is short
                profile_info["full_name"] = line
                break
        
        # Extract headline (usually after name, contains job title and keywords)
        headline_match = re.search(
            r"(Head of|Senior|Lead|Manager|Engineer|Developer|AI|ML|Data|Product).*?(\||$)",
            text,
            re.IGNORECASE
        )
        if headline_match:
            profile_info["headline"] = headline_match.group(0).strip("| ")
        
        # Extract location (look for city, country pattern)
        location_match = re.search(
            r"([A-Z][a-z]+),\s*([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)?)",
            text
        )
        if location_match:
            profile_info["location"] = location_match.group(0)
        
        # Extract "About" or "Summary" section
        about_match = re.search(
            r"(?:About|Summary)\s*\n((?:[^\n]*\n?){1,10}?)(?=\n(?:Experience|Education|Skills|#))",
            text,
            re.IGNORECASE | re.MULTILINE
        )
        if about_match:
            profile_info["about"] = about_match.group(1).strip()
        
        # Extract skills (usually after "Skills" section)
        skills_section = re.search(
            r"Skills\s*\n([\s\S]*?)(?=\n(?:Experience|Education|Languages|#)|$)",
            text,
            re.IGNORECASE
        )
        if skills_section:
            skills_text = skills_section.group(1)
            skills = [s.strip() for s in re.split(r"[,\n]", skills_text) if s.strip()]
            profile_info["skills"] = skills[:20]  # Limit to 20 skills
        
        # Extract experience (look for job titles with duration)
        exp_matches = re.finditer(
            r"([A-Z][a-z\s]+(?:Engineer|Manager|Lead|Developer|Scientist|Analyst|Consultant))\s*\n([A-Z][a-z\s]+(?:Inc|Ltd|Corp|LLC)?)\s*(.*?)(?=\n[A-Z](?:[a-z\s]+(?:Engineer|Manager|Lead)|Education|Skills|$))",
            text,
            re.IGNORECASE | re.MULTILINE
        )
        
        for match in exp_matches:
            profile_info["work_history"].append({
                "title": match.group(1).strip(),
                "company": match.group(2).strip(),
                "description": match.group(3).strip() if match.group(3) else "",
                "location": "",
            })
        
        if profile_info["work_history"]:
            profile_info["current_position"] = profile_info["work_history"][0].get("title", "")
            profile_info["current_company"] = profile_info["work_history"][0].get("company", "")
            profile_info["years_of_experience"] = len(profile_info["work_history"])
        
        # Extract education
        edu_matches = re.finditer(
            r"([A-Z][a-z\s]+(?:University|School|College|Institute))\s*,?\s*([A-Za-z\s,]*(?:Degree|Master|Bachelor|PhD)?[A-Za-z\s,]*)\s*\n([\d\s\-]*)",
            text,
            re.IGNORECASE
        )
        
        for match in edu_matches:
            profile_info["education"].append({
                "school": match.group(1).strip(),
                "degree": match.group(2).strip(),
                "dates": match.group(3).strip() if match.group(3) else "",
            })
        
        return profile_info
    
    @staticmethod
    def extract_expertise_areas(skills: list[str], headline: str, about: str) -> list[str]:
        """Extract main expertise areas from combined data."""
        expertise_keywords = {
            "AI/ML": ["AI", "ML", "machine learning", "artificial intelligence", "deep learning", "neural", "algorithm"],
            "Data": ["data", "analytics", "BI", "data science", "ETL", "warehouse"],
            "Cloud": ["AWS", "GCP", "Azure", "cloud", "kubernetes", "docker"],
            "Backend": ["python", "java", "go", "rust", "backend", "microservices", "API"],
            "Frontend": ["react", "vue", "angular", "javascript", "CSS", "UI", "UX"],
            "DevOps": ["devops", "CI/CD", "kubernetes", "terraform", "infrastructure"],
            "Database": ["SQL", "NoSQL", "postgres", "mongodb", "redis", "database"],
            "NLP": ["NLP", "language", "text", "chatbot", "LLM", "transformer"],
            "Search": ["search", "elasticsearch", "retrieval", "recommendation", "ranking"],
            "MLOps": ["MLOps", "monitoring", "model deployment", "feature store"],
        }
        
        combined_text = f"{' '.join(skills)} {headline} {about}".lower()
        
        expertise = []
        for category, keywords in expertise_keywords.items():
            if any(kw.lower() in combined_text for kw in keywords):
                expertise.append(category)
        
        return expertise[:5]  # Return top 5 expertise areas
    
    @staticmethod
    def parse_profile(text: str, source_type: str = "json") -> dict[str, Any]:
        """Main entry point: parse profile based on source type."""
        try:
            if source_type == "json" or source_type.endswith(".json"):
                data = json.loads(text)
                profile = LinkedInProfileParser.parse_json_profile(data)
            else:  # PDF or DOCX (already extracted to text)
                profile = LinkedInProfileParser.parse_text_profile(text)
            
            # Extract expertise areas
            expertise = LinkedInProfileParser.extract_expertise_areas(
                profile["skills"],
                profile.get("headline", ""),
                profile.get("about", "")
            )
            profile["expertise_areas"] = expertise
            
            return profile
        except json.JSONDecodeError:
            # If JSON fails, treat as text
            return LinkedInProfileParser.parse_text_profile(text)
        except Exception as e:
            print(f"Error parsing profile: {e}")
            return {
                "full_name": "",
                "headline": "",
                "about": "",
                "location": "",
                "skills": [],
                "expertise_areas": [],
                "current_position": "",
                "current_company": "",
                "years_of_experience": 0,
                "work_history": [],
                "education": [],
            }
