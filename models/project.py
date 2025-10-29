"""
Project and Graphic Models

Data models for project management with full audit trail support.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict


@dataclass
class Graphic:
    """Individual graphic within a project"""
    id: str
    name: str
    psd_path: Optional[str] = None
    template_path: Optional[str] = None
    template_name: Optional[str] = None
    status: str = 'not_started'

    # Approval tracking with full audit trail
    approved: bool = False
    approved_by: Optional[str] = None  # Username/email of approver
    approved_at: Optional[str] = None  # ISO timestamp of approval
    locked: bool = False

    # Audit history - track all status changes and approvals
    audit_log: List[dict] = field(default_factory=list)

    # Processing data
    mappings: Optional[dict] = None
    conflicts: Optional[List] = None
    confidence_score: Optional[float] = None
    preview_path: Optional[str] = None
    script_path: Optional[str] = None
    aepx_output_path: Optional[str] = None
    error_message: Optional[str] = None
    notes: str = ''

    # Expression tracking
    has_expressions: bool = False
    expression_count: int = 0
    expression_confidence: Optional[float] = None

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    processed_at: Optional[str] = None

    def add_audit_entry(self, action: str, user: str, details: Optional[dict] = None):
        """Add entry to audit log"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'user': user,
            'details': details or {}
        }
        self.audit_log.append(entry)
        self.updated_at = entry['timestamp']

    def can_edit(self) -> bool:
        """Check if graphic can be edited"""
        return not self.locked

    def can_approve(self) -> bool:
        """Check if graphic can be approved"""
        return self.status in ['complete', 'needs_review'] and not self.approved

    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class Project:
    """Project containing multiple graphics"""
    id: str
    name: str
    client: str = ''
    description: str = ''
    status: str = 'active'  # active, archived, completed
    graphics: List[Graphic] = field(default_factory=list)

    # Project stats
    total_graphics: int = 0
    approved_count: int = 0
    pending_count: int = 0
    error_count: int = 0

    # Extensible metadata storage (Hard Card info, etc.)
    metadata: Dict = field(default_factory=dict)

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_graphic(self, graphic: Graphic):
        """Add a graphic to the project"""
        self.graphics.append(graphic)
        self.update_stats()

    def get_graphic(self, graphic_id: str) -> Optional[Graphic]:
        """Get a graphic by ID"""
        for graphic in self.graphics:
            if graphic.id == graphic_id:
                return graphic
        return None

    def remove_graphic(self, graphic_id: str) -> bool:
        """Remove a graphic from the project"""
        graphic = self.get_graphic(graphic_id)
        if graphic:
            self.graphics.remove(graphic)
            self.update_stats()
            return True
        return False

    def update_stats(self):
        """Update project statistics"""
        self.total_graphics = len(self.graphics)
        self.approved_count = sum(1 for g in self.graphics if g.approved)
        self.pending_count = sum(1 for g in self.graphics if not g.approved and g.status != 'error')
        self.error_count = sum(1 for g in self.graphics if g.status == 'error')
        self.updated_at = datetime.now().isoformat()

    def to_dict(self):
        """Convert to dictionary"""
        data = asdict(self)
        return data


class ProjectStore:
    """Persistent storage for projects"""

    def __init__(self, storage_path: str = 'projects.json'):
        self.storage_path = storage_path
        self.projects: List[Project] = []
        self.next_project_id = 1
        self.next_graphic_id = 1
        self.load()

    def load(self):
        """Load projects from storage"""
        if not os.path.exists(self.storage_path):
            self.save()  # Create empty file
            return

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            self.next_project_id = data.get('next_project_id', 1)
            self.next_graphic_id = data.get('next_graphic_id', 1)

            # Reconstruct projects
            self.projects = []
            for proj_data in data.get('projects', []):
                # Reconstruct graphics
                graphics = []
                for g_data in proj_data.get('graphics', []):
                    graphic = Graphic(**g_data)
                    graphics.append(graphic)

                # Remove graphics from project data before creating Project
                proj_data_copy = proj_data.copy()
                proj_data_copy.pop('graphics', None)

                # Create project with graphics
                project = Project(**proj_data_copy, graphics=graphics)
                self.projects.append(project)

        except Exception as e:
            print(f"Error loading projects: {e}")
            # Keep empty state if load fails

    def save(self):
        """Save projects to storage"""
        try:
            data = {
                'next_project_id': self.next_project_id,
                'next_graphic_id': self.next_graphic_id,
                'projects': [proj.to_dict() for proj in self.projects]
            }

            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"Error saving projects: {e}")
            raise

    def create_project(self, name: str, client: str = '', description: str = '') -> Project:
        """Create a new project"""
        project_id = f"proj_{self.next_project_id}"
        self.next_project_id += 1

        project = Project(
            id=project_id,
            name=name,
            client=client,
            description=description
        )

        self.projects.append(project)
        self.save()
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID"""
        for project in self.projects:
            if project.id == project_id:
                return project
        return None

    def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        project = self.get_project(project_id)
        if project:
            self.projects.remove(project)
            self.save()
            return True
        return False

    def create_graphic(self, project_id: str, name: str, psd_path: Optional[str] = None) -> Optional[Graphic]:
        """Create a new graphic in a project"""
        project = self.get_project(project_id)
        if not project:
            return None

        graphic_id = f"graphic_{self.next_graphic_id}"
        self.next_graphic_id += 1

        graphic = Graphic(
            id=graphic_id,
            name=name,
            psd_path=psd_path
        )

        project.add_graphic(graphic)
        self.save()
        return graphic

    def list_projects(self) -> List[Project]:
        """List all projects"""
        return self.projects
