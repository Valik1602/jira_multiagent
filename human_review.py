"""
Human evaluation workflow
Allows humans to review and score agent outputs
"""

import json
import os
from datetime import datetime

class HumanReviewer:
    def __init__(self, results_file):
        """
        results_file: path to evaluation_results_*.json
        """
        with open(results_file, 'r') as f:
            self.eval_results = json.load(f)
        
        self.human_reviews = []
        self.results_file = results_file
        
    def review_task(self, task_index):
        """Review a single task"""
        if task_index >= len(self.eval_results['results']):
            print(f"❌ Task {task_index} not found")
            return
        
        task = self.eval_results['results'][task_index]
        
        print("\n" + "="*60)
        print("🧑 HUMAN REVIEW")
        print("="*60)
        
        print(f"\n📋 Task: {task['name']}")
        print(f"📝 Prompt: {task['prompt']}")
        print(f"\n⏱️  Execution time: {task.get('time_seconds', 0)}s")
        print(f"🔧 Tool calls: {task.get('tool_calls', 0)}")
        
        # LLM Judge results
        if 'llm_judge' in task and task['llm_judge']:
            judge = task['llm_judge']
            print(f"\n🤖 LLM Judge Score: {judge.get('overall_score', 0):.2f}/1.0")
            print(f"   Accuracy: {judge.get('accuracy', 0):.2f}")
            print(f"   Completeness: {judge.get('completeness', 0):.2f}")
            print(f"   Tool Efficiency: {judge.get('tool_efficiency', 0):.2f}")
            print(f"   Source Quality: {judge.get('source_quality', 0):.2f}")
            print(f"\n💬 LLM Judge Feedback:")
            print(f"   {judge.get('feedback', 'N/A')}")
        
        # Error если есть
        if 'error' in task:
            print(f"\n❌ Error: {task['error']}")
            print("\n⚠️  This task failed with an error. Review not needed.")
            return
        
        print("\n" + "-"*60)
        print("🧑 YOUR TURN - Rate this output:")
        print("-"*60)
        
        # Human scores
        print("\nRate each criterion (0.0 - 1.0):")
        
        try:
            accuracy = float(input("  Factual Accuracy (0.0-1.0): "))
            completeness = float(input("  Completeness (0.0-1.0): "))
            quality = float(input("  Output Quality (0.0-1.0): "))
            efficiency = float(input("  Tool Efficiency (0.0-1.0): "))
            
            overall = (accuracy + completeness + quality + efficiency) / 4
            
            feedback = input("\n💬 Your feedback (optional): ")
            
            human_review = {
                "task_name": task['name'],
                "task_index": task_index,
                "human_scores": {
                    "accuracy": accuracy,
                    "completeness": completeness,
                    "quality": quality,
                    "efficiency": efficiency,
                    "overall": overall
                },
                "human_feedback": feedback,
                "llm_judge_score": task.get('llm_judge', {}).get('overall_score', 0),
                "timestamp": datetime.now().isoformat()
            }
            
            self.human_reviews.append(human_review)
            
            print(f"\n✅ Review saved! Your score: {overall:.2f}/1.0")
            print(f"   LLM Judge score: {task.get('llm_judge', {}).get('overall_score', 0):.2f}/1.0")
            print(f"   Difference: {abs(overall - task.get('llm_judge', {}).get('overall_score', 0)):.2f}")
            
        except ValueError:
            print("❌ Invalid input. Skipping this review.")
    
    def review_all(self):
        """Review all tasks interactively"""
        print("\n🎯 HUMAN EVALUATION SESSION")
        print("="*60)
        print(f"Total tasks: {len(self.eval_results['results'])}")
        print("\nYou will review each task and rate the agent's output.")
        print("Press Ctrl+C at any time to exit and save.\n")
        
        try:
            for i in range(len(self.eval_results['results'])):
                self.review_task(i)
                
                if i < len(self.eval_results['results']) - 1:
                    cont = input("\n➡️  Continue to next task? (y/n): ")
                    if cont.lower() != 'y':
                        break
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Review interrupted by user")
        
        self.save_reviews()
    
    def save_reviews(self):
        """Save human reviews to file"""
        if not self.human_reviews:
            print("\n⚠️  No reviews to save")
            return
        
        filename = f"human_reviews_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        output = {
            "source_eval_file": self.results_file,
            "timestamp": datetime.now().isoformat(),
            "total_reviews": len(self.human_reviews),
            "reviews": self.human_reviews
        }
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n💾 Human reviews saved to: {filename}")
        
        # Summary
        avg_human = sum(r['human_scores']['overall'] for r in self.human_reviews) / len(self.human_reviews)
        avg_llm = sum(r['llm_judge_score'] for r in self.human_reviews) / len(self.human_reviews)
        
        print(f"\n📊 Summary:")
        print(f"   Reviews completed: {len(self.human_reviews)}")
        print(f"   Average human score: {avg_human:.2f}/1.0")
        print(f"   Average LLM Judge score: {avg_llm:.2f}/1.0")
        print(f"   Average difference: {abs(avg_human - avg_llm):.2f}")

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python human_review.py <evaluation_results_file.json>")
        print("\nExample:")
        print("  python human_review.py evaluation_results_20260427_212355.json")
        return
    
    results_file = sys.argv[1]
    
    if not os.path.exists(results_file):
        print(f"❌ File not found: {results_file}")
        return
    
    reviewer = HumanReviewer(results_file)
    reviewer.review_all()

if __name__ == "__main__":
    main()