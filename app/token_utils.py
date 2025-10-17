"""
Token tracking utilities using tiktoken.

Provides functions to count tokens and calculate costs for LLM API calls.
"""

import json

import tiktoken

# Initialize tokenizer for GPT-4o-mini (cl100k_base encoding)
tokenizer = tiktoken.get_encoding("cl100k_base")

# Cost per 1M tokens (GPT-4o-mini via OpenRouter)
INPUT_COST_PER_1M = 0.15  # $0.15 per 1M input tokens
OUTPUT_COST_PER_1M = 0.60  # $0.60 per 1M output tokens


def count_tokens(text) -> int:
    """
    Count tokens in text using tiktoken.

    Args:
        text: Text to count tokens for. Can be string, dict, or any JSON-serializable type.

    Returns:
        Number of tokens in the text.
    """
    if isinstance(text, dict):
        text = json.dumps(text)
    return len(tokenizer.encode(str(text)))


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """
    Calculate cost based on token counts.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Total cost in USD
    """
    input_cost = (input_tokens / 1_000_000) * INPUT_COST_PER_1M
    output_cost = (output_tokens / 1_000_000) * OUTPUT_COST_PER_1M
    return input_cost + output_cost


def format_token_stats(input_tokens: int, output_tokens: int) -> dict:
    """
    Format token statistics for display.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Dictionary with formatted token statistics
    """
    total_tokens = input_tokens + output_tokens
    cost = calculate_cost(input_tokens, output_tokens)

    stats = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost": cost,
    }

    # Add distribution percentages if tokens exist
    if total_tokens > 0:
        stats["input_percentage"] = (input_tokens / total_tokens) * 100
        stats["output_percentage"] = (output_tokens / total_tokens) * 100

    return stats


def print_token_stats(input_tokens: int, output_tokens: int, prefix: str = ""):
    """
    Print formatted token statistics.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        prefix: Optional prefix for indentation
    """
    stats = format_token_stats(input_tokens, output_tokens)

    print(f"{prefix}{'─' * 80}")
    print(f"{prefix}📊 Token Usage:")
    print(f"{prefix}   📥 Input:  {stats['input_tokens']:,} tokens")
    print(f"{prefix}   📤 Output: {stats['output_tokens']:,} tokens")
    print(f"{prefix}   🔢 Total:  {stats['total_tokens']:,} tokens")
    print(f"{prefix}   💰 Cost:   ${stats['cost']:.4f}")
    print(f"{prefix}{'─' * 80}\n")


class TokenTracker:
    """Track cumulative token usage across multiple API calls."""

    def __init__(self):
        """Initialize token tracker."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.call_count = 0

    def add_usage(self, input_tokens: int, output_tokens: int):
        """
        Add token usage to the tracker.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += calculate_cost(input_tokens, output_tokens)
        self.call_count += 1

    def get_stats(self) -> dict:
        """
        Get cumulative statistics.

        Returns:
            Dictionary with cumulative token statistics
        """
        total_tokens = self.total_input_tokens + self.total_output_tokens
        stats = {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": total_tokens,
            "total_cost": self.total_cost,
            "call_count": self.call_count,
        }

        if self.call_count > 0:
            stats["avg_cost_per_call"] = self.total_cost / self.call_count
            stats["avg_tokens_per_call"] = total_tokens / self.call_count

        if total_tokens > 0:
            stats["input_percentage"] = (self.total_input_tokens / total_tokens) * 100
            stats["output_percentage"] = (self.total_output_tokens / total_tokens) * 100

        return stats

    def print_summary(self, title: str = "CUMULATIVE TOKEN USAGE"):
        """
        Print cumulative token statistics summary.

        Args:
            title: Title for the summary section
        """
        if self.call_count == 0:
            return

        stats = self.get_stats()

        print(f"\n{'─' * 80}")
        print(f"📊 {title}:")
        print(f"{'─' * 80}")
        print(f"   📥 Total Input Tokens:  {stats['total_input_tokens']:,}")
        print(f"   📤 Total Output Tokens: {stats['total_output_tokens']:,}")
        print(f"   🔢 Total Tokens:        {stats['total_tokens']:,}")
        print(f"   💰 Total Cost:          ${stats['total_cost']:.4f}")
        print(f"   📈 API Calls:           {stats['call_count']}")

        if "avg_cost_per_call" in stats:
            print(f"   📉 Avg Cost per call:   ${stats['avg_cost_per_call']:.4f}")
            print(f"   📏 Avg Tokens per call: {stats['avg_tokens_per_call']:.0f}")

        print(f"{'─' * 80}")

        # Token distribution
        if "input_percentage" in stats:
            print("\n   Token Distribution:")
            print(
                f"   • Input:  {stats['input_percentage']:.1f}% ({stats['total_input_tokens']:,} tokens)"
            )
            print(
                f"   • Output: {stats['output_percentage']:.1f}% ({stats['total_output_tokens']:,} tokens)"
            )

    def reset(self):
        """Reset all counters to zero."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.call_count = 0
