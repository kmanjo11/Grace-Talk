#!/usr/bin/env python3
"""
Schedule Review Setup Tool
==========================
Comprehensive setup script for AI-assisted schedule analysis and reviews.
Establishes foundation for schedule reviews with specification compliance checking.

Usage: python3 schedule_review_setup.py
"""

import os
import sys
from pathlib import Path
from xerparser.reader import Reader
import pandas as pd

class ScheduleReviewSetup:
    def __init__(self):
        self.xer_file = None
        self.narrative_file = None
        self.spec_file = None
        self.schedule_data = None
        self.review_type = None
        self.project_info = {}
        
    def welcome_banner(self):
        """Display welcome banner and instructions"""
        print("="*70)
        print("🔍 SCHEDULE REVIEW SETUP TOOL")
        print("="*70)
        print("This tool establishes the foundation for AI-assisted schedule analysis.")
        print("It will:")
        print("• Parse XER files using PyP6XER")
        print("• Process specification documents as 'law of the land'")
        print("• Analyze narrative documents for context and contestable statements")
        print("• Set up reference framework for technical analysis")
        print("="*70)
        
    def detect_files(self):
        """Auto-detect relevant files in upload directory"""
        upload_dir = Path("/home/ubuntu/upload")
        
        print("\n📁 DETECTING FILES...")
        
        # Find XER files
        xer_files = list(upload_dir.glob("*.xer"))
        if xer_files:
            self.xer_file = str(xer_files[0])
            print(f"✅ XER File: {Path(self.xer_file).name}")
        
        # Find narrative files (PDF with "narrative" or "network analysis")
        narrative_files = []
        for pdf_file in upload_dir.glob("*.pdf"):
            if any(keyword in pdf_file.name.lower() for keyword in ['narrative', 'network', 'analysis', 'monthly']):
                narrative_files.append(pdf_file)
        
        if narrative_files:
            self.narrative_file = str(narrative_files[0])
            print(f"✅ Narrative: {Path(self.narrative_file).name}")
        
        # Find specification files
        spec_files = []
        for file in upload_dir.glob("*"):
            if any(keyword in file.name.lower() for keyword in ['spec', 'specification', 'rfp', 'contract']):
                spec_files.append(file)
        
        if spec_files:
            self.spec_file = str(spec_files[0])
            print(f"✅ Specification: {Path(self.spec_file).name}")
        
        # Manual file selection if needed
        if not self.xer_file:
            print("❌ No XER file detected. Please specify manually.")
            return False
            
        return True
    
    def determine_review_type(self):
        """Determine type of schedule review"""
        print("\n📋 REVIEW TYPE SELECTION:")
        print("1. Single Schedule Review (baseline, update, rebaseline)")
        print("2. Schedule Comparison (baseline vs update, before vs after)")
        print("3. Time Impact Analysis (TIA) Review")
        print("4. Delay Analysis Review")
        
        while True:
            try:
                choice = input("\nSelect review type (1-4): ").strip()
                if choice in ['1', '2', '3', '4']:
                    review_types = {
                        '1': 'single_schedule',
                        '2': 'schedule_comparison', 
                        '3': 'tia_review',
                        '4': 'delay_analysis'
                    }
                    self.review_type = review_types[choice]
                    print(f"✅ Review Type: {self.review_type.replace('_', ' ').title()}")
                    break
                else:
                    print("Please enter 1, 2, 3, or 4")
            except KeyboardInterrupt:
                print("\nSetup cancelled.")
                return False
        return True
    
    def parse_xer_file(self):
        """Parse XER file using PyP6XER"""
        print(f"\n⚙️  PARSING XER FILE: {Path(self.xer_file).name}")
        
        try:
            reader = Reader(self.xer_file)
            
            # Get basic project info
            projects = list(reader.projects)
            if projects:
                project = projects[0]
                self.project_info = {
                    'id': getattr(project, 'id', 'Unknown'),
                    'name': getattr(project, 'proj_short_name', getattr(project, 'name', 'Unknown')),
                    'start_date': getattr(project, 'plan_start_date', 'Unknown'),
                    'finish_date': getattr(project, 'plan_end_date', 'Unknown')
                }
            
            # Get counts
            activities = list(reader.tasks)
            relationships = list(reader.predecessors)
            resources = list(reader.resources)
            wbs_elements = list(reader.wbss)
            
            self.schedule_data = {
                'reader': reader,
                'activities': activities,
                'relationships': relationships,
                'resources': resources,
                'wbs_elements': wbs_elements,
                'activity_count': len(activities),
                'relationship_count': len(relationships),
                'resource_count': len(resources),
                'wbs_count': len(wbs_elements)
            }
            
            print(f"✅ Successfully parsed XER file:")
            print(f"   • Project: {self.project_info['name']}")
            print(f"   • Activities: {len(activities):,}")
            print(f"   • Relationships: {len(relationships):,}")
            print(f"   • Resources: {len(resources):,}")
            print(f"   • WBS Elements: {len(wbs_elements):,}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error parsing XER file: {e}")
            return False
    
    def analyze_lags(self):
        """Quick lag analysis"""
        print(f"\n🔗 ANALYZING RELATIONSHIP LAGS...")
        
        relationships_with_lags = []
        lag_summary = {}
        
        for rel in self.schedule_data['relationships']:
            if hasattr(rel, 'lag_hr_cnt') and rel.lag_hr_cnt and rel.lag_hr_cnt != 0:
                relationships_with_lags.append(rel)
                lag_days = rel.lag_hr_cnt / 8
                lag_summary[lag_days] = lag_summary.get(lag_days, 0) + 1
        
        print(f"✅ Lag Analysis Complete:")
        print(f"   • Relationships with lags: {len(relationships_with_lags)}")
        print(f"   • Percentage with lags: {(len(relationships_with_lags)/len(self.schedule_data['relationships']))*100:.1f}%")
        
        if lag_summary:
            print(f"   • Lag distribution:")
            for lag_days, count in sorted(lag_summary.items()):
                print(f"     - {lag_days:+.1f} days: {count} relationships")
        
        return relationships_with_lags
    
    def setup_specification_framework(self):
        """Set up specification reference framework"""
        print(f"\n📖 SPECIFICATION FRAMEWORK SETUP...")
        
        spec_framework = {
            'reference_format': 'Specification [SECTION] [SUBSECTION]',
            'example': 'Specification 013210 D.7.b',
            'page_numbering': 'RFP package footer format: [SECTION]-[PAGE] (starts page 10)',
            'section_format': '[NUMBER].[SUBSECTION] [TITLE]',
            'example_section': '011000-1 (1.1)A for "1.1 PROJECT IDENTIFICATION A. Project Name and Location"'
        }
        
        print(f"✅ Specification Reference Framework:")
        print(f"   • Format: {spec_framework['reference_format']}")
        print(f"   • Example: {spec_framework['example']}")
        print(f"   • Page Reference: {spec_framework['page_numbering']}")
        print(f"   • Section Example: {spec_framework['example_section']}")
        
        return spec_framework
    
    def create_analysis_context(self):
        """Create comprehensive analysis context for AI"""
        print(f"\n🤖 CREATING AI ANALYSIS CONTEXT...")
        
        context = {
            'project_info': self.project_info,
            'schedule_data': {
                'activity_count': self.schedule_data['activity_count'],
                'relationship_count': self.schedule_data['relationship_count'],
                'resource_count': self.schedule_data['resource_count'],
                'wbs_count': self.schedule_data['wbs_count']
            },
            'files': {
                'xer_file': self.xer_file,
                'narrative_file': self.narrative_file,
                'spec_file': self.spec_file
            },
            'review_type': self.review_type,
            'analysis_capabilities': [
                'Schedule logic analysis',
                'Float calculations', 
                'Critical path identification',
                'Lag analysis',
                'Resource analysis',
                'Specification compliance checking',
                'Narrative statement validation'
            ]
        }
        
        print(f"✅ Analysis Context Created:")
        print(f"   • Review Type: {self.review_type.replace('_', ' ').title()}")
        print(f"   • Files Available: {len([f for f in context['files'].values() if f])}")
        print(f"   • Analysis Capabilities: {len(context['analysis_capabilities'])}")
        
        return context
    
    def generate_ai_instructions(self):
        """Generate instructions for AI assistant"""
        instructions = f"""
🤖 AI ASSISTANT INSTRUCTIONS FOR SCHEDULE REVIEW
================================================

PROJECT CONTEXT:
• Project: {self.project_info.get('name', 'Unknown')}
• Review Type: {self.review_type.replace('_', ' ').title()}
• Activities: {self.schedule_data['activity_count']:,}
• Relationships: {self.schedule_data['relationship_count']:,}

ANALYSIS FRAMEWORK:
1. Use PyP6XER for all schedule data parsing
2. Reference specifications as "law of the land" 
3. Format spec references as: "Specification [SECTION] [SUBSECTION]"
4. Contest narrative statements when they violate specifications
5. Provide evidence-based analysis with specific activity references

AVAILABLE TOOLS:
• XER File: {Path(self.xer_file).name if self.xer_file else 'None'}
• Narrative: {Path(self.narrative_file).name if self.narrative_file else 'None'}
• Specifications: {Path(self.spec_file).name if self.spec_file else 'None'}

KEY ANALYSIS AREAS:
• Schedule logic and relationships
• Float analysis and critical path
• Specification compliance
• Contractor vs owner responsibility
• Non-compensable delays
• Resource and crew management

READY FOR SCHEDULE REVIEW ANALYSIS!
"""
        return instructions
    
    def run_setup(self):
        """Run complete setup process"""
        self.welcome_banner()
        
        if not self.detect_files():
            return False
            
        if not self.determine_review_type():
            return False
            
        if not self.parse_xer_file():
            return False
            
        self.analyze_lags()
        spec_framework = self.setup_specification_framework()
        context = self.create_analysis_context()
        instructions = self.generate_ai_instructions()
        
        print("\n" + "="*70)
        print("🎯 SETUP COMPLETE - READY FOR SCHEDULE REVIEW!")
        print("="*70)
        print(instructions)
        
        # Save context for reference
        with open('/home/ubuntu/schedule_review_context.txt', 'w') as f:
            f.write(instructions)
        
        print(f"\n💾 Context saved to: schedule_review_context.txt")
        print(f"📁 All files ready for AI analysis")
        
        return True

def main():
    """Main execution function"""
    setup = ScheduleReviewSetup()
    success = setup.run_setup()
    
    if success:
        print(f"\n✅ Schedule review setup completed successfully!")
        print(f"🚀 You can now proceed with detailed schedule analysis.")
    else:
        print(f"\n❌ Setup failed. Please check files and try again.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())