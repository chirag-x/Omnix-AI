class ShortTermMemory:
    def __init__(self, max_history=15):
        self.history = []
        self.skill_history = []
        self.max_history = max_history
        
    def add_message(self, role: str, content: str):
        # If this is a new observation, strip massive UI dumps from older messages to save context
        if role == "user" and "Observation Results:\n[" in content:
            for msg in self.history:
                if msg["role"] == "user" and "Observation Results:\n[" in msg["content"]:
                    # Truncate old observation
                    goal_part = msg["content"].split("\nObservation Results:\n[")[0]
                    msg["content"] = f"{goal_part}\nObservation Results:\n[Old Observation Truncated to save memory]"
                    
        self.history.append({"role": role, "content": content})
        
        # Enforce rolling buffer (curable amnesia)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
    def get_history(self) -> list:
        return self.history
        
    def track_skill(self, skill: str, args: dict):
        # Store only the skill name for loop detection — slight coord differences still count as the same action
        self.skill_history.append(skill)
        
    def is_looping(self) -> bool:
        # 3-strike rule: same SKILL NAME 3 times in a row regardless of args (catches slightly different coords)
        if len(self.skill_history) >= 3:
            last_three = self.skill_history[-3:]
            if last_three[0] == last_three[1] == last_three[2]:
                if last_three[0] == "observe":
                    # Allow up to 6 consecutive observes then give up
                    if len(self.skill_history) >= 6 and all(s == "observe" for s in self.skill_history[-6:]):
                        return True
                    return False
                return True
        return False

    def total_steps(self) -> int:
        return len(self.skill_history)
        
    def clear(self):
        self.history = []
        self.skill_history = []
