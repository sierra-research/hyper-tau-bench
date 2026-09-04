import argparse
import json

from tau2.config import (
    DEFAULT_AGENT_IMPLEMENTATION,
    DEFAULT_AUDIO_NATIVE_MODELS,
    DEFAULT_AUDIO_NATIVE_PROVIDER,
    DEFAULT_INTEGRATION_DURATION_SECONDS,
    DEFAULT_INTERRUPTION_CHECK_INTERVAL_SECONDS,
    DEFAULT_LLM_AGENT,
    DEFAULT_LLM_EVAL_USER_SIMULATOR,
    DEFAULT_LLM_LOG_MODE,
    DEFAULT_LLM_TEMPERATURE_AGENT,
    DEFAULT_LLM_TEMPERATURE_USER,
    DEFAULT_LLM_USER,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_MAX_ERRORS,
    DEFAULT_MAX_STEPS,
    DEFAULT_MAX_STEPS_SECONDS,
    DEFAULT_NUM_TRIALS,
    DEFAULT_PCM_SAMPLE_RATE,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_MIN_WAIT,
    DEFAULT_SEED,
    DEFAULT_SILENCE_ANNOTATION_THRESHOLD_SECONDS,
    DEFAULT_SPEECH_COMPLEXITY,
    DEFAULT_TELEPHONY_RATE,
    DEFAULT_TICK_DURATION_SECONDS,
    DEFAULT_USER_IMPLEMENTATION,
    DEFAULT_WAIT_TO_RESPOND_THRESHOLD_OTHER_SECONDS,
    DEFAULT_WAIT_TO_RESPOND_THRESHOLD_SELF_SECONDS,
    DEFAULT_YIELD_THRESHOLD_WHEN_INTERRUPTED_SECONDS,
    DEFAULT_YIELD_THRESHOLD_WHEN_INTERRUPTING_SECONDS,
)
from tau2.data_model.persona import PersonaConfig
from tau2.data_model.simulation import (
    AudioNativeConfig,
    TextRunConfig,
    VoiceRunConfig,
)
from tau2.domains.banking_knowledge.retrieval import get_all_variant_names
from tau2.hyper.harnesses.factory import (
    DEFAULT_DEVELOPER_HARNESS,
    DEVELOPER_HARNESSES,
    create_developer_builder,
)
from tau2.hyper.run_defaults import (
    DEFAULT_CLIENT_LLM,
    DEFAULT_CLIENT_REASONING_EFFORT,
    DEFAULT_DEVELOPER_LLM,
)
from tau2.run import get_options, run_domain
from tau2.runner.work import parse_provider_limits


def get_all_retrieval_config_names():
    return get_all_variant_names()


def add_run_args(parser):
    """Add run arguments to a parser."""
    domains = get_options().domains
    parser.add_argument(
        "--domain",
        "-d",
        type=str,
        choices=domains,
        help="The domain to run the simulation on",
    )
    parser.add_argument(
        "--num-trials",
        type=int,
        default=DEFAULT_NUM_TRIALS,
        help="The number of times each task is run. Default is 1.",
    )
    parser.add_argument(
        "--agent",
        type=str,
        default=DEFAULT_AGENT_IMPLEMENTATION,
        choices=get_options().agents,
        help=f"The agent implementation to use. Default is {DEFAULT_AGENT_IMPLEMENTATION}.",
    )
    parser.add_argument(
        "--agent-llm",
        type=str,
        default=DEFAULT_LLM_AGENT,
        help=f"The LLM to use for the agent. Default is {DEFAULT_LLM_AGENT}.",
    )
    parser.add_argument(
        "--agent-llm-args",
        type=json.loads,
        default={"temperature": DEFAULT_LLM_TEMPERATURE_AGENT},
        help=f"The arguments to pass to the LLM for the agent. Default is '{{\"temperature\": {DEFAULT_LLM_TEMPERATURE_AGENT}}}'.",
    )
    parser.add_argument(
        "--user",
        type=str,
        choices=get_options().users,
        default=DEFAULT_USER_IMPLEMENTATION,
        help=f"The user implementation to use. Default is {DEFAULT_USER_IMPLEMENTATION}.",
    )
    parser.add_argument(
        "--user-llm",
        type=str,
        default=DEFAULT_LLM_USER,
        help=f"The LLM to use for the user. Default is {DEFAULT_LLM_USER}.",
    )
    parser.add_argument(
        "--user-llm-args",
        type=json.loads,
        default={"temperature": DEFAULT_LLM_TEMPERATURE_USER},
        help=f"The arguments to pass to the LLM for the user. Default is '{{\"temperature\": {DEFAULT_LLM_TEMPERATURE_USER}}}'.",
    )
    parser.add_argument(
        "--task-set-name",
        type=str,
        default=None,
        choices=get_options().task_sets,
        help="The task set to run the simulation on. If not provided, will load default task set for the domain.",
    )
    parser.add_argument(
        "--task-split-name",
        type=str,
        default="base",
        help="The task split to run the simulation on. If not provided, will load 'base' split.",
    )
    parser.add_argument(
        "--task-ids",
        type=str,
        nargs="+",
        help="(Optional) run only the tasks with the given IDs. If not provided, will run all tasks.",
    )
    parser.add_argument(
        "--num-tasks",
        type=int,
        default=None,
        help="The number of tasks to run.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=DEFAULT_MAX_STEPS,
        help=f"The maximum number of steps to run the simulation. Default is {DEFAULT_MAX_STEPS}.",
    )
    parser.add_argument(
        "--max-errors",
        type=int,
        default=DEFAULT_MAX_ERRORS,
        help=f"The maximum number of tool errors allowed in a row in the simulation. Default is {DEFAULT_MAX_ERRORS}.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Maximum wallclock time in seconds for each simulation. No timeout by default.",
    )
    parser.add_argument(
        "--save-to",
        type=str,
        required=False,
        help="The path to save the simulation results. Will be saved to data/simulations/<save_to>/results.json. If not provided, will save to <timestamp>_<domain>_<agent>_<user>. If the file already exists, it will try to resume the run.",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=DEFAULT_MAX_CONCURRENCY,
        help=f"The maximum number of concurrent simulations to run. Default is {DEFAULT_MAX_CONCURRENCY}. "
        "With --workers, this is the number of simulations each worker process holds.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="Number of worker processes to spawn. 0 (default) runs simulations in this "
        "process. N > 0 makes this process a controller that schedules and checkpoints "
        "while N worker processes execute (N x --max-concurrency simulations in flight); "
        "use when scaling beyond the single-process concurrency ceiling.",
    )
    parser.add_argument(
        "--provider-limit",
        type=str,
        default=None,
        help='Per-provider concurrency caps in controller mode, e.g. "openai=40,gemini=20". '
        "Requires --workers.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"The seed to use for the simulation. Default is {DEFAULT_SEED}.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=DEFAULT_LOG_LEVEL,
        help=f"The log level to use for the simulation. Default is {DEFAULT_LOG_LEVEL}.",
    )
    parser.add_argument(
        "--verbose-logs",
        action="store_true",
        default=False,
        help="Enable verbose logging: saves LLM call logs, audio files, per-task logs, and ticks (for audio-native). "
        "Files are saved to the save directory (auto-generated if --save-to not specified).",
    )
    parser.add_argument(
        "--audio-debug",
        action="store_true",
        default=False,
        help="Enable audio debugging for audio-native mode. Saves per-tick audio files and timing "
        "analysis report for diagnosing alignment issues. Requires --audio-native.",
    )
    parser.add_argument(
        "--audio-taps",
        action="store_true",
        default=False,
        help="Enable audio tap recording for audio-native mode. Saves WAV files at each pipeline "
        "stage (pre-effects, post-noise, post-telephony, final, agent-input) for diagnosing "
        "signal property differences. Requires --audio-native.",
    )
    parser.add_argument(
        "--llm-log-mode",
        type=str,
        choices=["all", "latest"],
        default=DEFAULT_LLM_LOG_MODE,
        help="LLM debug logging mode. Only takes effect when --verbose-logs is enabled. "
        "'all' saves every LLM call (can generate many files), "
        "'latest' keeps only the most recent call of each type (saves space). "
        f"Default is '{DEFAULT_LLM_LOG_MODE}'. Ignored if --verbose-logs is not specified.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_RETRY_ATTEMPTS,
        help=f"Maximum number of retries for failed tasks. Default is {DEFAULT_RETRY_ATTEMPTS}.",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=DEFAULT_RETRY_MIN_WAIT,
        help=f"Delay in seconds between retries. Default is {DEFAULT_RETRY_MIN_WAIT}.",
    )
    parser.add_argument(
        "--enforce-communication-protocol",
        action="store_true",
        default=False,
        help="Enforce communication protocol rules (e.g., no mixed messages with text and tool calls). Default is False.",
    )
    parser.add_argument(
        "--user-persona",
        type=json.loads,
        default=None,
        help="User persona config as JSON dict. Supports explicit values or weighted probabilities. "
        'Examples: \'{"verbosity": "minimal"}\', '
        '\'{"verbosity": {"minimal": 0.8, "standard": 0.2}}\'. '
        "If not provided, uses default behavior (standard verbosity).",
    )

    # Audio-native mode arguments
    parser.add_argument(
        "--audio-native",
        action="store_true",
        default=False,
        help="Enable audio-native mode using DiscreteTimeAudioNativeAgent with VoiceStreamingUserSimulator. "
        "This enables full-duplex voice simulation using audio native APIs.",
    )
    parser.add_argument(
        "--audio-native-provider",
        type=str,
        choices=["openai", "gemini", "xai", "nova", "qwen", "livekit"],
        default=DEFAULT_AUDIO_NATIVE_PROVIDER,
        help=f"Audio native API provider. Default is '{DEFAULT_AUDIO_NATIVE_PROVIDER}'.",
    )
    parser.add_argument(
        "--cascaded-config",
        type=str,
        default=None,
        help="Cascaded config preset name for livekit provider. "
        "Available presets: 'default', 'openai-thinking'. "
        "See tau2.voice.audio_native.livekit.config for details.",
    )
    parser.add_argument(
        "--audio-native-model",
        type=str,
        default=None,
        help="Audio native model to use. If not specified, uses the default model for the selected provider.",
    )
    parser.add_argument(
        "--reasoning-effort",
        type=str,
        choices=["minimal", "low", "medium", "high", "xhigh"],
        default=None,
        help="Reasoning effort for thinking models. Only applies to providers that support it (e.g. OpenAI).",
    )
    parser.add_argument(
        "--tick-duration",
        type=float,
        default=DEFAULT_TICK_DURATION_SECONDS,
        help=f"Tick duration in seconds for audio-native mode. Default is {DEFAULT_TICK_DURATION_SECONDS}.",
    )
    parser.add_argument(
        "--max-steps-seconds",
        type=int,
        default=DEFAULT_MAX_STEPS_SECONDS,
        help=f"Maximum conversation duration in seconds for audio-native mode. Default is {DEFAULT_MAX_STEPS_SECONDS}.",
    )
    parser.add_argument(
        "--speech-complexity",
        type=str,
        choices=[
            "control",
            "regular",
            # Single-feature ablations
            "control_audio",
            "control_accents",
            "control_behavior",
            # Pairwise ablations
            "control_audio_accents",
            "control_audio_behavior",
            "control_accents_behavior",
        ],
        default=DEFAULT_SPEECH_COMPLEXITY,
        help=f"Speech complexity level for audio effects. Default is '{DEFAULT_SPEECH_COMPLEXITY}'.",
    )

    # Audio-native: Sample rates
    parser.add_argument(
        "--pcm-sample-rate",
        type=int,
        default=DEFAULT_PCM_SAMPLE_RATE,
        help=f"User simulator PCM synthesis sample rate. Default is {DEFAULT_PCM_SAMPLE_RATE}.",
    )
    parser.add_argument(
        "--telephony-rate",
        type=int,
        default=DEFAULT_TELEPHONY_RATE,
        help=f"API/agent telephony sample rate (OpenAI Realtime API). Default is {DEFAULT_TELEPHONY_RATE}.",
    )

    # Audio-native: Turn-taking thresholds
    parser.add_argument(
        "--wait-to-respond-other",
        type=float,
        default=DEFAULT_WAIT_TO_RESPOND_THRESHOLD_OTHER_SECONDS,
        help=f"Min time since OTHER (agent) spoke before user responds (seconds). Default is {DEFAULT_WAIT_TO_RESPOND_THRESHOLD_OTHER_SECONDS}.",
    )
    parser.add_argument(
        "--wait-to-respond-self",
        type=float,
        default=DEFAULT_WAIT_TO_RESPOND_THRESHOLD_SELF_SECONDS,
        help=f"Min time since SELF (user) spoke before responding (seconds). Default is {DEFAULT_WAIT_TO_RESPOND_THRESHOLD_SELF_SECONDS}.",
    )
    parser.add_argument(
        "--yield-when-interrupted",
        type=float,
        default=DEFAULT_YIELD_THRESHOLD_WHEN_INTERRUPTED_SECONDS,
        help=f"How long user keeps speaking when agent interrupts (seconds). Default is {DEFAULT_YIELD_THRESHOLD_WHEN_INTERRUPTED_SECONDS}.",
    )
    parser.add_argument(
        "--yield-when-interrupting",
        type=float,
        default=DEFAULT_YIELD_THRESHOLD_WHEN_INTERRUPTING_SECONDS,
        help=f"How long user keeps speaking when user interrupts agent (seconds). Default is {DEFAULT_YIELD_THRESHOLD_WHEN_INTERRUPTING_SECONDS}.",
    )
    parser.add_argument(
        "--interruption-check-interval",
        type=float,
        default=DEFAULT_INTERRUPTION_CHECK_INTERVAL_SECONDS,
        help=f"Interval for checking interruptions (seconds). Default is {DEFAULT_INTERRUPTION_CHECK_INTERVAL_SECONDS}.",
    )
    parser.add_argument(
        "--integration-duration",
        type=float,
        default=DEFAULT_INTEGRATION_DURATION_SECONDS,
        help=f"Integration duration for linearization (seconds). Default is {DEFAULT_INTEGRATION_DURATION_SECONDS}.",
    )
    parser.add_argument(
        "--silence-annotation-threshold",
        type=float,
        default=DEFAULT_SILENCE_ANNOTATION_THRESHOLD_SECONDS,
        help=f"Silence threshold for adding annotations to conversation history (seconds). Default is {DEFAULT_SILENCE_ANNOTATION_THRESHOLD_SECONDS}.",
    )

    # Audio-native: Agent behavior flags
    parser.add_argument(
        "--buffer-until-complete",
        action="store_true",
        default=False,
        help="Buffer audio until complete utterance — OpenAI provider only. Default is disabled.",
    )
    parser.add_argument(
        "--fast-forward",
        action="store_true",
        default=False,
        help="Enable fast-forward mode — OpenAI provider only (run as fast as possible instead of real-time). Default is disabled.",
    )
    parser.add_argument(
        "--send-audio-instant",
        action="store_true",
        default=False,
        help="Send audio instantly (all at once per tick) instead of streaming at real-time rate. Default is streaming (non-instant).",
    )

    # Prompt format
    prompt_format_group = parser.add_mutually_exclusive_group()
    prompt_format_group.add_argument(
        "--xml-prompt",
        action="store_true",
        default=False,
        help="Use XML tags in system prompt (overrides auto-detection).",
    )
    prompt_format_group.add_argument(
        "--no-xml-prompt",
        action="store_true",
        default=False,
        help="Use plain text system prompt without XML tags (overrides auto-detection).",
    )

    # Knowledge domain arguments
    parser.add_argument(
        "--retrieval-config",
        type=str,
        default=None,
        choices=sorted(get_all_retrieval_config_names()),
        help=(
            "Knowledge retrieval config name (banking_knowledge domain). "
            "Offline: no_knowledge, full_kb, golden_retrieval, bm25, bm25_grep, grep_only. "
            "Requires OPENAI_API_KEY: openai_embeddings*, alltools. "
            "Requires OPENROUTER_API_KEY: qwen_embeddings*, alltools-qwen. "
            "Requires sandbox-runtime: terminal_use*, alltools, alltools-qwen. "
            "Default for banking_knowledge: alltools (BM25 + dense + shell)."
        ),
    )
    parser.add_argument(
        "--retrieval-config-kwargs",
        type=json.loads,
        default=None,
        help="Arguments to pass to the retrieval config constructor as JSON (e.g., '{\"top_k\": 10}').",
    )

    # Resume mode
    parser.add_argument(
        "--auto-resume",
        action="store_true",
        default=False,
        help="Automatically resume from existing save file without prompting (for non-interactive runs).",
    )

    # Auto-review mode
    parser.add_argument(
        "--auto-review",
        action="store_true",
        default=False,
        help="Automatically run LLM conversation review after each simulation.",
    )
    parser.add_argument(
        "--review-mode",
        type=str,
        choices=["full", "user"],
        default="full",
        help="Review mode when --auto-review is enabled: 'full' (agent+user errors, default) or 'user' (user simulator only).",
    )
    parser.add_argument(
        "--review-model",
        type=str,
        default=DEFAULT_LLM_EVAL_USER_SIMULATOR,
        help=f"LLM model to use for review calls. Default is {DEFAULT_LLM_EVAL_USER_SIMULATOR}.",
    )
    parser.add_argument(
        "--hallucination-retries",
        type=int,
        default=3,
        help="Max retries when a user simulator hallucination is detected (full-duplex only). Set to 0 to disable.",
    )


def _get_version() -> str:
    from tau2.utils.utils import get_tau2_version

    return get_tau2_version()


def run_intro():
    """Display a rich intro page describing what tau2-bench can do."""
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    console = Console()
    version = _get_version()

    # ── Banner ──────────────────────────────────────────────────────────
    banner = Text(justify="center")
    banner.append("\n")
    banner.append("tau2-bench", style="bold cyan")
    banner.append(f"  v{version}\n", style="dim")
    banner.append(
        "A simulation framework for evaluating\n"
        "conversational customer-service agents\n",
        style="italic",
    )
    console.print(
        Panel(
            banner,
            border_style="cyan",
            padding=(1, 4),
        )
    )

    # ── Modes ───────────────────────────────────────────────────────────
    modes_table = Table(
        title="Communication Modes",
        box=box.SIMPLE_HEAVY,
        title_style="bold magenta",
        show_edge=False,
        pad_edge=False,
        padding=(0, 2),
    )
    modes_table.add_column("Mode", style="bold", no_wrap=True)
    modes_table.add_column("Description")
    modes_table.add_row(
        "Half-duplex (text)",
        "Turn-based text conversations. Agent and user take turns exchanging messages.",
    )
    modes_table.add_row(
        "Full-duplex (voice)",
        "Real-time audio-native voice using streaming APIs (OpenAI, Gemini, xAI, Nova, Qwen, Deepgram).",
    )
    console.print(modes_table)
    console.print()

    # ── Domains ─────────────────────────────────────────────────────────
    domain_table = Table(
        title="Domains",
        box=box.SIMPLE_HEAVY,
        title_style="bold magenta",
        show_edge=False,
        pad_edge=False,
        padding=(0, 2),
    )
    domain_table.add_column("Domain", style="bold", no_wrap=True)
    domain_table.add_column("Description")
    domain_table.add_row(
        "airline", "Flight booking, cancellation, and customer support"
    )
    domain_table.add_row("retail", "Order management, returns, and product inquiries")
    domain_table.add_row("telecom", "Telecom account management and troubleshooting")
    domain_table.add_row("mock", "Lightweight test domain for development")
    console.print(domain_table)
    console.print()

    # ── Commands ────────────────────────────────────────────────────────
    cmd_table = Table(
        title="Commands",
        box=box.SIMPLE_HEAVY,
        title_style="bold magenta",
        show_edge=False,
        pad_edge=False,
        padding=(0, 2),
    )
    cmd_table.add_column("Command", style="bold green", no_wrap=True)
    cmd_table.add_column("What it does")
    cmd_table.add_row("tau2 run", "Run a benchmark evaluation against a domain")
    cmd_table.add_row("tau2 view", "Browse and inspect simulation results")
    cmd_table.add_row(
        "tau2 play", "Interactive manual mode \u2014 play the agent yourself"
    )
    cmd_table.add_row("tau2 domain <name>", "Show detailed documentation for a domain")
    cmd_table.add_row(
        "tau2 review <path>", "Run LLM-based conversation review on results"
    )
    cmd_table.add_row(
        "tau2 evaluate-trajs <paths>", "Re-evaluate trajectories and recompute rewards"
    )
    cmd_table.add_row("tau2 check-data", "Verify data directory is set up correctly")
    cmd_table.add_row(
        "tau2 hyper-tau <task>",
        "Run a Hyper-τ evaluation (CLI visualizer)",
    )
    cmd_table.add_row(
        "tau2 hyper-tau-app",
        "Launch interactive Hyper-τ web visualizer",
    )
    cmd_table.add_row("tau2 start", "Start background servers")
    cmd_table.add_row("tau2 intro", "Show this page")
    console.print(cmd_table)
    console.print()

    # ── Quick Start ─────────────────────────────────────────────────────
    from rich.syntax import Syntax

    quick_start = (
        "# 1. Verify your setup\n"
        "tau2 check-data\n"
        "\n"
        "# 2. Run a text (half-duplex) evaluation\n"
        "tau2 run --domain airline --agent-llm gpt-4.1 --user-llm gpt-4.1 "
        "--num-trials 1 --num-tasks 5\n"
        "\n"
        "# 3. Run a voice (full-duplex) evaluation\n"
        "tau2 run --domain retail --audio-native --num-tasks 1 --verbose-logs\n"
        "\n"
        "# 4. Browse results\n"
        "tau2 view"
    )
    console.print(
        Panel(
            Syntax(quick_start, "bash", theme="monokai", line_numbers=False),
            title="[bold yellow]Quick Start[/bold yellow]",
            border_style="yellow",
            padding=(1, 2),
        )
    )

    # ── Tip ─────────────────────────────────────────────────────────────
    console.print(
        "\n[dim]Tip: Run any command with [bold]--help[/bold] for detailed usage, "
        "e.g. [bold green]tau2 run --help[/bold green][/dim]\n"
    )


def main():
    parser = argparse.ArgumentParser(description="Tau2 command line interface")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a benchmark")
    add_run_args(run_parser)

    def run_command(args):
        user_persona_config = None
        if args.user_persona:
            user_persona_config = PersonaConfig.from_dict(args.user_persona)  # noqa: F841

        # Build audio-native config if enabled
        audio_native_config = None
        if args.audio_native:
            # Resolve model based on provider if not specified
            audio_native_model = args.audio_native_model
            if audio_native_model is None:
                audio_native_model = DEFAULT_AUDIO_NATIVE_MODELS[
                    args.audio_native_provider
                ]

            # Determine use_xml_prompt: defaults to False (plain text)
            use_xml_prompt = False
            if args.xml_prompt:
                use_xml_prompt = True

            audio_native_config = AudioNativeConfig(
                # Provider
                provider=args.audio_native_provider,
                model=audio_native_model,
                cascaded_config_name=args.cascaded_config,
                reasoning_effort=args.reasoning_effort,
                # Timing
                tick_duration_seconds=args.tick_duration,
                max_steps_seconds=args.max_steps_seconds,
                # Sample rates
                pcm_sample_rate=args.pcm_sample_rate,
                telephony_rate=args.telephony_rate,
                # Turn-taking thresholds
                wait_to_respond_threshold_other_seconds=args.wait_to_respond_other,
                wait_to_respond_threshold_self_seconds=args.wait_to_respond_self,
                yield_threshold_when_interrupted_seconds=args.yield_when_interrupted,
                yield_threshold_when_interrupting_seconds=args.yield_when_interrupting,
                interruption_check_interval_seconds=args.interruption_check_interval,
                integration_duration_seconds=args.integration_duration,
                silence_annotation_threshold_seconds=args.silence_annotation_threshold,
                # Agent behavior
                buffer_until_complete=args.buffer_until_complete,
                fast_forward_mode=args.fast_forward,
                send_audio_instant=args.send_audio_instant,
                use_xml_prompt=use_xml_prompt,
            )

        # Set global LLM log mode (used by verbose logging)
        from tau2.utils.llm_utils import set_llm_log_mode

        set_llm_log_mode(args.llm_log_mode)

        # Shared config kwargs
        shared_kwargs = dict(
            domain=args.domain,
            task_set_name=args.task_set_name,
            task_split_name=args.task_split_name,
            task_ids=args.task_ids,
            num_tasks=args.num_tasks,
            llm_user=args.user_llm,
            llm_args_user=args.user_llm_args,
            num_trials=args.num_trials,
            max_errors=args.max_errors,
            timeout=args.timeout,
            save_to=args.save_to,
            max_concurrency=args.max_concurrency,
            workers=args.workers,
            provider_limits=parse_provider_limits(args.provider_limit),
            seed=args.seed,
            log_level=args.log_level,
            verbose_logs=args.verbose_logs,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay,
            auto_resume=args.auto_resume,
            auto_review=args.auto_review,
            review_mode=args.review_mode,
            review_model=args.review_model,
            hallucination_retries=args.hallucination_retries,
            retrieval_config=args.retrieval_config,
            retrieval_config_kwargs=args.retrieval_config_kwargs,
        )

        if audio_native_config is not None:
            config = VoiceRunConfig(
                **shared_kwargs,
                audio_native_config=audio_native_config,
                speech_complexity=args.speech_complexity,
                audio_debug=getattr(args, "audio_debug", False),
                audio_taps=getattr(args, "audio_taps", False),
            )
        else:
            config = TextRunConfig(
                **shared_kwargs,
                agent=args.agent,
                llm_agent=args.agent_llm,
                llm_args_agent=args.agent_llm_args,
                user=args.user,
                max_steps=args.max_steps,
                enforce_communication_protocol=args.enforce_communication_protocol,
            )

        return run_domain(config)

    run_parser.set_defaults(func=run_command)

    # Play command
    play_parser = subparsers.add_parser(
        "play", help="Play manual mode - interact with a domain as the agent"
    )
    play_parser.set_defaults(func=lambda args: run_manual_mode())

    # View command
    view_parser = subparsers.add_parser("view", help="View simulation results")
    view_parser.add_argument(
        "--dir",
        type=str,
        help="Directory containing simulation files. Defaults to data/simulations if not specified.",
    )
    view_parser.add_argument(
        "--file",
        type=str,
        help="Path to the simulation results file to view",
    )
    view_parser.add_argument(
        "--only-show-failed",
        action="store_true",
        help="Only show failed tasks.",
    )
    view_parser.add_argument(
        "--only-show-all-failed",
        action="store_true",
        help="Only show tasks that failed in all trials.",
    )
    view_parser.add_argument(
        "--expanded-ticks",
        action="store_true",
        help="Show expanded tick view instead of consolidated (for full-duplex simulations).",
    )
    view_parser.add_argument(
        "--max-tool-result-chars",
        type=int,
        default=500,
        help="Truncate tool results (e.g. retrieved knowledge articles) to this many characters. Default: 500.",
    )
    view_parser.add_argument(
        "--full-tool-results",
        action="store_true",
        help="Show full tool results without truncation.",
    )
    view_parser.set_defaults(func=lambda args: run_view_simulations(args))

    # Domain command
    domain_parser = subparsers.add_parser("domain", help="Show domain documentation")
    domain_parser.add_argument(
        "domain",
        type=str,
        help="Name of the domain to show documentation for (e.g., 'airline', 'mock')",
    )
    domain_parser.set_defaults(func=lambda args: run_show_domain(args))

    # Start command
    start_parser = subparsers.add_parser("start", help="Start all servers")
    start_parser.set_defaults(func=lambda args: run_start_servers())

    # Worker command (executes simulations for a `tau2 run --workers N` controller)
    worker_parser = subparsers.add_parser(
        "worker",
        help="Run a worker process that executes simulations for a tau2 controller "
        "(see `tau2 run --workers`).",
    )
    worker_parser.add_argument(
        "--controller",
        type=str,
        required=True,
        help="Controller base URL, e.g. http://127.0.0.1:8321",
    )
    worker_parser.add_argument(
        "--slots",
        type=int,
        default=10,
        help="Concurrent simulations this worker holds (default: 10).",
    )
    worker_parser.add_argument(
        "--worker-id",
        type=str,
        default=None,
        help="Worker identity in controller logs (default: hostname-pid).",
    )

    def worker_command(args):
        from tau2.runner.worker import run_worker_command

        return run_worker_command(
            controller=args.controller, slots=args.slots, worker_id=args.worker_id
        )

    worker_parser.set_defaults(func=worker_command)

    # Intro command
    intro_parser = subparsers.add_parser(
        "intro", help="Show an overview of tau2-bench and available commands"
    )
    intro_parser.set_defaults(func=lambda args: run_intro())

    # Check data command
    check_data_parser = subparsers.add_parser(
        "check-data", help="Check if data directory is properly configured"
    )
    check_data_parser.set_defaults(func=lambda args: run_check_data())

    # Evaluate trajectories command
    evaluate_parser = subparsers.add_parser(
        "evaluate-trajs", help="Evaluate trajectories and update rewards"
    )
    evaluate_parser.add_argument(
        "paths",
        nargs="+",
        help="Paths to trajectory files, directories, or glob patterns",
    )
    evaluate_parser.add_argument(
        "-o",
        "--output-dir",
        help="Directory to save updated trajectory files with recomputed rewards. If not provided, only displays metrics.",
    )
    evaluate_parser.add_argument(
        "--fresh-tasks",
        action="store_true",
        help="Re-grade against the current task definitions from the data directory instead of the ones embedded in each results file.",
    )
    evaluate_parser.set_defaults(func=lambda args: run_evaluate_trajectories(args))

    # Review command - LLM-based conversation review
    review_parser = subparsers.add_parser(
        "review", help="Run LLM-based conversation review on simulation results"
    )
    review_parser.add_argument(
        "path",
        help="Path to a results.json file or a directory containing results.json files",
    )
    review_parser.add_argument(
        "-m",
        "--mode",
        type=str,
        choices=["full", "user"],
        default="full",
        help="Review mode: 'full' (agent+user, default) or 'user' (user simulator only)",
    )
    review_parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output path for the reviewed results (only used for single file)",
    )
    review_parser.add_argument(
        "--interruption-enabled",
        action="store_true",
        help="Flag indicating that interruption was enabled for these simulations",
    )
    review_parser.add_argument(
        "--show-details",
        action="store_true",
        help="Show detailed review results for each simulation",
    )
    review_parser.add_argument(
        "-c",
        "--max-concurrency",
        type=int,
        default=32,
        help="Maximum number of concurrent reviews (default: 32)",
    )
    review_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit review to first N simulations",
    )
    review_parser.add_argument(
        "--task-ids",
        type=str,
        nargs="+",
        default=None,
        help="Only review simulations for these task IDs",
    )
    review_parser.add_argument(
        "--log-llm",
        action="store_true",
        help="Log LLM request/response for each review call",
    )
    review_parser.add_argument(
        "--review-model",
        type=str,
        default=DEFAULT_LLM_EVAL_USER_SIMULATOR,
        help=f"LLM model to use for review calls. Default is {DEFAULT_LLM_EVAL_USER_SIMULATOR}.",
    )
    review_parser.set_defaults(func=lambda args: run_review(args))

    # Submit command with subcommands
    submit_parser = subparsers.add_parser(
        "submit", help="Submission management for the leaderboard"
    )
    submit_subparsers = submit_parser.add_subparsers(
        dest="submit_command", help="Submit subcommands", required=True
    )

    # Hyper-τ command
    hyper_tau_parser = subparsers.add_parser(
        "hyper-tau",
        help="Run a Hyper-τ outer-loop evaluation with live visualization",
    )
    hyper_tau_parser.add_argument(
        "task_id",
        type=str,
        nargs="?",
        default=None,
        help="ID of the Hyper-τ task to run (e.g. '008_retail_plus_construction_core_evidence_performance_hard').",
    )
    hyper_tau_parser.add_argument(
        "--developer-llm",
        type=str,
        default=DEFAULT_DEVELOPER_LLM,
        help=f"LLM for the Developer agent. Default: {DEFAULT_DEVELOPER_LLM}.",
    )
    hyper_tau_parser.add_argument(
        "--client-llm",
        type=str,
        default=None,
        help=(
            "Optional LLM override for the Client simulator. Default: the "
            f"task's 'client_llm', then {DEFAULT_CLIENT_LLM}."
        ),
    )
    hyper_tau_parser.add_argument(
        "--agent-llm",
        type=str,
        default=None,
        help=(
            "Optional single-model override for the inner-loop Agent. Default: "
            "use the task's allowed model profile."
        ),
    )
    hyper_tau_parser.add_argument(
        "--primary-model-only",
        action="store_true",
        help=(
            "For a task with one stock performance tier, expose only that "
            "tier's designated highest-scoring open-weight model to the "
            "constructed agent. The tier's mean-credit cap is unchanged."
        ),
    )
    hyper_tau_parser.add_argument(
        "--user-llm",
        type=str,
        default=None,
        help=(
            "Optional LLM override for the inner-loop User simulator. Default: "
            "use the task configuration."
        ),
    )
    hyper_tau_parser.add_argument(
        "--developer-reasoning-effort",
        type=str,
        default="medium",
        choices=["none", "low", "medium", "high", "xhigh"],
        help=(
            "Reasoning effort for the Developer model/harness. Default: medium. "
            "Supported native harnesses pass this to their own CLI."
        ),
    )
    hyper_tau_parser.add_argument(
        "--developer-thinking-budget",
        type=int,
        default=None,
        help="Thinking budget tokens for Developer LLM (Anthropic claude models).",
    )
    hyper_tau_parser.add_argument(
        "--client-reasoning-effort",
        type=str,
        default=None,
        choices=["none", "low", "medium", "high", "xhigh"],
        help=(
            "Reasoning effort for the Client LLM (OpenAI gpt-5.x models). "
            "Default: the task's 'client_reasoning_effort', then "
            f"{DEFAULT_CLIENT_REASONING_EFFORT}."
        ),
    )
    hyper_tau_parser.add_argument(
        "--client-thinking-budget",
        type=int,
        default=None,
        help="Thinking budget tokens for Client LLM (Anthropic claude models).",
    )
    hyper_tau_parser.add_argument(
        "--agent-reasoning-effort",
        type=str,
        default=None,
        choices=["none", "low", "medium", "high", "xhigh"],
        help=(
            "Reasoning effort for an explicit --agent-llm override. Default: "
            "use the selected task profile's constraint."
        ),
    )
    hyper_tau_parser.add_argument(
        "--agent-thinking-budget",
        type=int,
        default=None,
        help="Thinking budget tokens for Agent LLM (Anthropic claude models).",
    )
    hyper_tau_parser.add_argument(
        "--user-reasoning-effort",
        type=str,
        default=None,
        choices=["none", "low", "medium", "high", "xhigh"],
        help=(
            "Reasoning effort for an explicit --user-llm override. Default: "
            "use the task configuration."
        ),
    )
    hyper_tau_parser.add_argument(
        "--user-thinking-budget",
        type=int,
        default=None,
        help="Thinking budget tokens for User LLM (Anthropic claude models).",
    )
    hyper_tau_parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Show full tool results without truncation.",
    )
    hyper_tau_parser.add_argument(
        "--no-display",
        action="store_true",
        default=False,
        help="Disable the live visualizer (just log to console).",
    )
    hyper_tau_parser.add_argument(
        "--list-tasks",
        action="store_true",
        default=False,
        help="List available Hyper-τ task IDs and exit.",
    )
    hyper_tau_parser.add_argument(
        "--allow-legacy-domain",
        action="store_true",
        default=False,
        help=(
            "Allow frozen airline/retail Hyper-τ baselines for an explicitly "
            "requested ablation. Maintained work should use airline_plus or "
            "retail_plus."
        ),
    )
    hyper_tau_parser.add_argument(
        "--compile-report",
        action="store_true",
        default=False,
        help=(
            "Compile the task's SOP variant and print the transformation "
            "fact-coverage report (covered / fallback / multiply "
            "represented facts) without running anything."
        ),
    )
    hyper_tau_parser.add_argument(
        "--developer-harness",
        choices=DEVELOPER_HARNESSES,
        default=DEFAULT_DEVELOPER_HARNESS,
        help=(
            "Coding harness used by the sandbox Developer. The model is "
            "selected separately with --developer-llm. Use 'codex' (default), "
            "'claude-code', or the open-source harnesses 'opencode' and "
            "'prime-agent'."
        ),
    )
    hyper_tau_parser.add_argument(
        "--sandbox-steps",
        type=int,
        default=0,
        help=(
            "Optional maximum number of recorded sandbox build steps. "
            "Default: 0 (no step limit)."
        ),
    )
    hyper_tau_parser.add_argument(
        "--sandbox-timeout",
        type=int,
        default=None,
        help=(
            "Hard wall-clock limit in seconds for sandbox mode. Default: "
            "the task value, or 28800 (8 hours) when unset. An explicit CLI "
            "value overrides task metadata; legacy task values of 0 select "
            "the benchmark default."
        ),
    )
    hyper_tau_parser.add_argument(
        "--kit-dir",
        type=str,
        default=None,
        help="Explicit directory for the sandbox kit. If not set, uses a temp dir.",
    )
    hyper_tau_parser.add_argument(
        "--keep-kit",
        action="store_true",
        default=False,
        help="Don't clean up the kit directory after sandbox mode finishes.",
    )
    hyper_tau_parser.set_defaults(func=lambda args: run_hyper_tau(args))

    # Hyper-τ web app command
    hyper_tau_app_parser = subparsers.add_parser(
        "hyper-tau-app",
        help="Launch the Hyper-τ benchmark workbench (kit assembly and runs)",
    )
    hyper_tau_app_parser.add_argument(
        "--port",
        type=int,
        default=8888,
        help="Port to run the web app on. Default: 8888.",
    )
    hyper_tau_app_parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to. Default: 0.0.0.0.",
    )
    hyper_tau_app_parser.set_defaults(func=lambda args: run_hyper_tau_app(args))

    # Hyper-τ Client-simulator tooling
    hyper_client_parser = subparsers.add_parser(
        "hyper-client",
        help="Hyper-τ Client simulator tooling (render)",
    )
    hyper_client_subparsers = hyper_client_parser.add_subparsers(
        dest="hyper_client_command", required=True
    )

    def _add_hyper_client_common_args(parser):
        parser.add_argument(
            "--domain",
            type=str,
            required=True,
            help="Source domain with section fact schemas (e.g. airline).",
        )
        parser.add_argument(
            "--sections",
            type=str,
            nargs="+",
            default=None,
            help="Section ids to include. Default: every section with a schema.",
        )
        parser.add_argument(
            "--manifest",
            type=str,
            default=None,
            help=(
                "Variant manifest path (data-relative) whose client_knowledge "
                "bundle members mark the facts the Client alone holds."
            ),
        )

    hyper_client_render_parser = hyper_client_subparsers.add_parser(
        "render",
        help="Render the Client instructions for inspection",
    )
    _add_hyper_client_common_args(hyper_client_render_parser)
    hyper_client_render_parser.set_defaults(func=run_hyper_client_render)

    # Submit interaction-metrics subcommand
    submit_im_parser = submit_subparsers.add_parser(
        "interaction-metrics",
        help="Compute voice interaction metrics (latency, responsiveness, "
        "interrupts, selectivity) from full-duplex trajectories",
    )
    submit_im_parser.add_argument(
        "input_paths",
        nargs="+",
        help="Voice experiment directories (results.json + simulations/) or a "
        "parent directory such as a submission's trajectories/ dir",
    )
    submit_im_parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Optional path to write the interaction_metrics JSON block",
    )
    submit_im_parser.set_defaults(func=lambda args: run_interaction_metrics(args))

    # Convert results format command
    convert_parser = subparsers.add_parser(
        "convert-results",
        help="Convert simulation results between storage formats",
    )
    convert_parser.add_argument(
        "path",
        help="Path to results.json or results directory to convert",
    )
    convert_parser.add_argument(
        "--to",
        dest="target_format",
        choices=["json", "dir"],
        default=None,
        help="Target format: 'json' (monolithic) or 'dir' (directory with individual sim files). "
        "If omitted, converts to the opposite of the current format.",
    )
    convert_parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating a .bak backup of the original file",
    )
    convert_parser.set_defaults(func=lambda args: run_convert_results(args))

    # Model routing: show which key / endpoint serves each model id
    routing_parser = subparsers.add_parser(
        "model-routing",
        help=(
            "Show how model_routing.toml routes every model id (provider, "
            "upstream id, API key variable) and which keys are missing."
        ),
    )
    routing_parser.add_argument(
        "--task",
        type=str,
        default=None,
        help=(
            "Restrict the model list to one Hyper-τ task's menu plus the run "
            "defaults (Client/User simulators, judge, Developer)."
        ),
    )
    routing_parser.add_argument(
        "--all-tasks",
        action="store_true",
        help="Cover every release task's menu instead of the manifest's [models].",
    )
    routing_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any required API key variable is unset.",
    )
    routing_parser.set_defaults(func=lambda args: run_model_routing(args))

    args = parser.parse_args()
    if not hasattr(args, "func"):
        run_intro()
        return

    args.func(args)


def run_view_simulations(args):
    from tau2.scripts.view_simulations import main as view_main

    if args.full_tool_results or args.max_tool_result_chars <= 0:
        max_tool_result_length = None
    else:
        max_tool_result_length = args.max_tool_result_chars

    view_main(
        sim_file=args.file,
        only_show_failed=args.only_show_failed,
        only_show_all_failed=args.only_show_all_failed,
        sim_dir=args.dir,
        expanded_ticks=args.expanded_ticks,
        max_tool_result_length=max_tool_result_length,
    )


def run_show_domain(args):
    from tau2.scripts.show_domain_doc import main as domain_main

    domain_main(args.domain)


def run_start_servers():
    from tau2.scripts.start_servers import main as start_main

    start_main()


def run_check_data():
    from tau2.scripts.check_data import main as check_data_main

    check_data_main()


def run_evaluate_trajectories(args):
    import sys

    from loguru import logger

    from tau2.scripts.evaluate_trajectories import evaluate_trajectories

    logger.configure(handlers=[{"sink": sys.stderr, "level": "ERROR"}])

    evaluate_trajectories(
        args.paths, args.output_dir, fresh_tasks=getattr(args, "fresh_tasks", False)
    )


def run_review(args):
    """Run LLM-based conversation review."""
    import sys
    from pathlib import Path

    from loguru import logger
    from rich.console import Console

    from tau2.scripts.review_conversation import ReviewMode, find_results_files, review

    logger.configure(handlers=[{"sink": sys.stderr, "level": "WARNING"}])

    # Find all results files
    input_path = Path(args.path)
    results_files = find_results_files(input_path)

    if not results_files:
        console = Console()
        console.print(f"[red]No results.json files found in: {args.path}[/red]")
        sys.exit(1)

    # Run review for each results file
    mode = ReviewMode.FULL if args.mode == "full" else ReviewMode.USER
    console = Console()

    if len(results_files) > 1:
        console.print(
            f"\n📁 Found {len(results_files)} results files to review:",
            style="bold blue",
        )
        for i, rf in enumerate(results_files, 1):
            console.print(f"  {i}. {rf.parent.name}/results.json")
        console.print()

    for i, results_file in enumerate(results_files):
        if len(results_files) > 1:
            console.print(
                f"\n{'=' * 60}\n[bold cyan]Processing ({i + 1}/{len(results_files)}): {results_file.parent.name}[/bold cyan]\n{'=' * 60}"
            )

        review(
            results_path=str(results_file),
            mode=mode,
            output_path=args.output if len(results_files) == 1 else None,
            interruption_enabled=args.interruption_enabled,
            show_details=args.show_details,
            max_concurrency=args.max_concurrency,
            limit=args.limit,
            task_ids=args.task_ids,
            log_llm=args.log_llm,
            review_model=args.review_model,
        )


def run_interaction_metrics(args):
    """Run the interaction metrics computation command."""
    from tau2.scripts.leaderboard.compute_interaction_metrics import (
        compute_interaction_metrics,
    )

    compute_interaction_metrics(
        input_paths=args.input_paths,
        output_path=args.output,
    )


def run_manual_mode():
    from tau2.scripts.manual_mode import main as manual_main

    manual_main()


def _build_hyper_tau_llm_args(
    model: str | None,
    reasoning_effort: str | None,
    thinking_budget: int | None,
) -> dict | None:
    """Build LLM args dict from reasoning parameters for Hyper-τ models.

    - OpenAI reasoning models (gpt-5.*): use ``reasoning_effort``.
    - Anthropic models (claude-*): use ``thinking`` with ``budget_tokens``.

    Returns None if no reasoning parameters are set.
    """
    if model is None:
        if reasoning_effort is not None or thinking_budget is not None:
            raise ValueError(
                "A model must be selected when overriding reasoning or thinking"
            )
        return None

    args_dict: dict = {}

    if reasoning_effort and model.startswith("gpt-5"):
        args_dict["reasoning_effort"] = reasoning_effort

    if thinking_budget and "claude" in model:
        args_dict["thinking"] = {
            "type": "enabled",
            "budget_tokens": thinking_budget,
        }

    return args_dict if args_dict else None


def run_hyper_tau(args):
    """Run a Hyper-τ outer-loop evaluation with live visualization.

    This is currently the **only** working entry point for running a
    Hyper-τ task end-to-end. The intended promoted path
    (``tau2 run --domain hyper_<source_domain>``) is registered in
    ``tau2.registry`` but not yet wired through the standard runner;
    that's a planned follow-up. Until then, this command remains the
    supported way to run Hyper-τ.
    """
    import sys

    from rich.console import Console

    # Notice on stderr so scripts that parse stdout aren't affected.
    # `stderr=True` is a `Console.__init__` argument, not a `print()` kwarg.
    notice_console = Console(stderr=True)
    notice_console.print(
        "[yellow]Notice: `tau2 hyper-tau` is the current working entry "
        "point for running Hyper-τ tasks end-to-end. The promoted path "
        "`tau2 run --domain hyper_<source_domain>` is registered for task "
        "discovery but the runner-side wiring is not yet in place — that's "
        "a planned follow-up. Anticipated flag mapping when it lands:"
        "[/yellow]\n"
        "  --developer-llm  →  --agent-llm\n"
        "  --client-llm     →  --user-llm\n"
        "  --agent-llm      →  --inner-agent-llm\n"
        "  --user-llm       →  --inner-user-llm\n"
    )
    console = Console()

    # Handle --list-tasks
    if args.list_tasks:
        from tau2.hyper.task_loader import load_active_hyper_tau_tasks

        tasks = load_active_hyper_tau_tasks(
            allow_legacy=args.allow_legacy_domain,
        )
        if not tasks:
            console.print("[red]No Hyper-τ tasks found.[/red]")
            sys.exit(1)

        from rich.table import Table

        table = Table(title="Available Hyper-τ Tasks", show_header=True)
        table.add_column("ID", style="bold cyan")
        table.add_column("Domain")

        for t in tasks:
            table.add_row(
                t.id,
                t.source_domain,
            )
        console.print(table)
        return

    # Require task_id if not listing
    if not args.task_id:
        console.print(
            "[red]Error: task_id is required. "
            "Use --list-tasks to see available tasks.[/red]"
        )
        sys.exit(1)

    # Load through the maintained-domain gate before audits or execution.
    from tau2.hyper.task_loader import (
        LegacyHyperTauDomainError,
        load_active_hyper_tau_task,
    )

    try:
        task = load_active_hyper_tau_task(
            args.task_id,
            allow_legacy=args.allow_legacy_domain,
        )
    except (FileNotFoundError, LegacyHyperTauDomainError) as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    # Handle transformation audits without starting an outer-loop run.
    if args.compile_report:
        from tau2.hyper.transformations import compile_hyper_task

        try:
            compilation = compile_hyper_task(task)
        except FileNotFoundError as e:
            console.print(f"[red]{e}[/red]")
            sys.exit(1)
        console.print(compilation.summary())
        sys.exit(1 if compilation.errors else 0)

    _run_hyper_tau_sandbox(args, task, console)


def _resolve_hyper_sandbox_limits(args, task) -> tuple[int, int]:
    """Resolve task defaults while preserving explicit CLI timeout overrides."""
    task_config = task.sandbox_config or {}
    sandbox_steps = getattr(args, "sandbox_steps", 0)
    if sandbox_steps == 0:
        sandbox_steps = task_config.get("max_steps", 0)

    sandbox_timeout = getattr(args, "sandbox_timeout", None)
    if sandbox_timeout is None:
        sandbox_timeout = task_config.get("max_time_seconds") or 8 * 60 * 60
    return sandbox_steps, sandbox_timeout


def _resolve_primary_model_override(args, task):
    """Resolve the optional primary-only model list for a sandbox run."""
    if not getattr(args, "primary_model_only", False):
        return None

    conflicting_flags = [
        flag
        for flag, value in (
            ("--agent-llm", getattr(args, "agent_llm", None)),
            (
                "--agent-reasoning-effort",
                getattr(args, "agent_reasoning_effort", None),
            ),
            (
                "--agent-thinking-budget",
                getattr(args, "agent_thinking_budget", None),
            ),
        )
        if value is not None
    ]
    if conflicting_flags:
        raise ValueError(
            "--primary-model-only cannot be combined with "
            + ", ".join(conflicting_flags)
        )
    if not isinstance(task.performance_profile, str):
        raise ValueError(
            "--primary-model-only requires one stock performance tier; "
            "multi-tier and custom tier profiles do not have one designated "
            "primary"
        )

    from tau2.hyper.performance_profiles import get_primary_model_config

    return [get_primary_model_config(task.performance_profile, task.source_domain)]


def _run_hyper_tau_sandbox(args, task, console):
    """Run a Hyper-τ construction task in its sandbox workspace."""
    from pathlib import Path

    from tau2.hyper.sandbox.builder import BuildBudget
    from tau2.hyper.sandbox.orchestrator import SandboxOrchestrator

    try:
        allowed_agent_models_override = _resolve_primary_model_override(args, task)
    except ValueError as error:
        console.print(f"[red]{error}[/red]")
        raise SystemExit(2) from error

    console.print(
        "\n[bold cyan]Running in SANDBOX mode[/bold cyan] — "
        "Developer uses filesystem + shell tools.\n"
    )

    # Build LLM args for the builder (uses --developer-llm flags)
    developer_llm_args = _build_hyper_tau_llm_args(
        args.developer_llm,
        getattr(args, "developer_reasoning_effort", None),
        getattr(args, "developer_thinking_budget", None),
    )
    agent_llm_args = _build_hyper_tau_llm_args(
        args.agent_llm,
        getattr(args, "agent_reasoning_effort", None),
        getattr(args, "agent_thinking_budget", None),
    )
    user_llm_args = _build_hyper_tau_llm_args(
        args.user_llm,
        getattr(args, "user_reasoning_effort", None),
        getattr(args, "user_thinking_budget", None),
    )

    # Build budget from args or task config
    sandbox_steps, sandbox_timeout = _resolve_hyper_sandbox_limits(args, task)

    budget = BuildBudget(
        max_steps=sandbox_steps,
        max_time_seconds=sandbox_timeout,
    )

    developer_harness = getattr(args, "developer_harness", DEFAULT_DEVELOPER_HARNESS)
    builder = create_developer_builder(
        developer_harness,
        args.developer_llm,
        developer_llm_args,
        getattr(args, "developer_reasoning_effort", None),
    )

    kit_dir = Path(args.kit_dir) if getattr(args, "kit_dir", None) else None
    keep_kit = getattr(args, "keep_kit", False)

    # Reasoning validity depends on the model family, so build the Client's
    # args against the model the run will actually seat.
    client_llm_args = _build_hyper_tau_llm_args(
        args.client_llm or task.client_llm or DEFAULT_CLIENT_LLM,
        getattr(args, "client_reasoning_effort", None),
        getattr(args, "client_thinking_budget", None),
    )

    orchestrator = SandboxOrchestrator.from_task(
        task=task,
        builder=builder,
        client_llm=args.client_llm,
        client_llm_args=client_llm_args,
        agent_llm=args.agent_llm,
        user_llm=args.user_llm,
        agent_llm_args=agent_llm_args,
        user_llm_args=user_llm_args,
        allowed_agent_models_override=allowed_agent_models_override,
        budget=budget,
        kit_dir=kit_dir,
        keep_kit=keep_kit,
    )

    # Build display
    from tau2.hyper.recording import RecordingDisplay

    inner_display = None
    if not args.no_display:
        from tau2.hyper.visualizer import HyperTauDisplay

        inner_display = HyperTauDisplay(console=console, verbose=args.verbose)

    run_config = {
        "mode": "sandbox",
        "developer_harness": developer_harness,
        "developer_llm": args.developer_llm,
        "developer_llm_args": developer_llm_args,
        "agent_llm": orchestrator.agent_llm,
        "agent_llm_args": orchestrator.agent_llm_args,
        "allowed_agent_models": orchestrator.allowed_agent_models,
        "primary_model_only": allowed_agent_models_override is not None,
        "user_llm": orchestrator.user_llm,
        "user_llm_args": orchestrator.user_llm_args,
        "legacy_sandbox_steps": sandbox_steps,
        "sandbox_wall_clock_seconds": sandbox_timeout,
    }
    recorder = RecordingDisplay(inner_display, task=task, config=run_config)

    # Run
    result = orchestrator.run(display=recorder)

    # Save recording
    save_path = recorder.save(task=task, result=result, config=run_config)
    console.print(f"\n[dim]Saved recording to: {save_path}[/dim]")
    console.print(f"[dim]Final test reward: {result.final_test_reward:.3f}[/dim]")


def run_hyper_tau_app(args):
    """Launch the Hyper-τ interactive web visualizer."""
    from tau2.hyper.web.app import start_app

    start_app(host=args.host, port=args.port)


def _hyper_client_manifest_facts(args):
    """(held, confirmable, contested) fact maps from --manifest (all empty without one).

    ``contested`` maps section ids to ``{fact_id: [readings]}`` — the
    declared divergent renditions the kit carries for those held facts.
    """
    if not getattr(args, "manifest", None):
        return {}, {}, {}
    from tau2.hyper.transformations import compile_variant_transformations
    from tau2.hyper.transformations.sop_variants import load_sop_variant_manifest

    manifest = load_sop_variant_manifest(args.manifest)
    compilation = compile_variant_transformations(manifest)
    compilation.raise_on_errors()
    return (
        compilation.client_held_fact_ids,
        compilation.client_confirmable_fact_ids,
        compilation.client_contested_fact_ids,
    )


def _render_hyper_client_instructions(args):
    """Shared render step for the hyper-client subcommands."""
    from tau2.hyper.client_sim.instructions import (
        list_section_ids,
        render_client_instructions,
    )

    section_ids = args.sections or list_section_ids(args.domain)
    held, confirmable, contested = _hyper_client_manifest_facts(args)
    return render_client_instructions(
        args.domain,
        section_ids,
        client_held=held,
        client_confirmable=confirmable,
        client_contested={
            section_id: sorted(facts) for section_id, facts in contested.items()
        },
    )


def run_hyper_client_render(args):
    """Print the rendered Client instructions."""
    rendered = _render_hyper_client_instructions(args)
    print(rendered.prompt)


def run_convert_results(args):
    """Convert simulation results between storage formats."""
    import shutil
    from pathlib import Path

    from tau2.data_model.simulation import Results

    path = Path(args.path)
    current_fmt = Results._detect_format(path)
    target_fmt = args.target_format

    if target_fmt is None:
        target_fmt = "json" if current_fmt == "dir" else "dir"

    if current_fmt == target_fmt:
        print(f"Results at {path} are already in '{target_fmt}' format.")
        return

    print(f"Converting {path}: '{current_fmt}' -> '{target_fmt}'")
    results = Results.load(path)

    meta_path = path if path.suffix == ".json" else path / "results.json"

    if not args.no_backup:
        if current_fmt == "json":
            backup = meta_path.with_suffix(".json.bak")
            shutil.copy2(meta_path, backup)
            print(f"  Backup: {backup}")
        else:
            sims_dir = meta_path.parent / "simulations"
            backup_dir = meta_path.parent / "simulations.bak"
            if sims_dir.exists():
                if backup_dir.exists():
                    shutil.rmtree(backup_dir)
                shutil.copytree(sims_dir, backup_dir)
            backup = meta_path.with_suffix(".json.bak")
            shutil.copy2(meta_path, backup)
            print(f"  Backup: {backup}")
            if backup_dir.exists():
                print(f"  Backup: {backup_dir}")

    if target_fmt == "dir":
        results.save(meta_path, format="dir")
    else:
        sims_dir = meta_path.parent / "simulations"
        results.save(meta_path, format="json")
        if sims_dir.exists():
            shutil.rmtree(sims_dir)

    n = len(results.simulations)
    print(f"  Done. {n} simulation(s) converted to '{target_fmt}' format.")


if __name__ == "__main__":
    main()


def _hyper_task_menu_models(task) -> list[str]:
    """Every model id a Hyper-τ task's performance profile can expose."""
    from tau2.hyper.performance_profiles import iter_profile_model_ids

    if task.performance_profile is None:
        return []
    return iter_profile_model_ids(task.performance_profile, task.source_domain)


def _model_routing_seat_defaults() -> dict[str, str]:
    from tau2.config import DEFAULT_LLM_NL_ASSERTIONS
    from tau2.hyper.run_defaults import (
        DEFAULT_CLIENT_LLM,
        DEFAULT_DEVELOPER_LLM,
        DEFAULT_USER_LLM,
    )

    return {
        DEFAULT_DEVELOPER_LLM: "Developer (--developer-llm default)",
        DEFAULT_CLIENT_LLM: "Client simulator",
        DEFAULT_USER_LLM: "User simulator",
        DEFAULT_LLM_NL_ASSERTIONS: "NL-assertion judge",
    }


def run_model_routing(args):
    """Print the resolved model routing table and check API key coverage."""
    import os

    from rich.console import Console
    from rich.table import Table

    from tau2.utils.model_routing import (
        ModelRoutingError,
        load_routing,
        routing_path,
    )

    console = Console()
    try:
        routing = load_routing()
    except ModelRoutingError as error:
        console.print(f"[red]{error}[/red]")
        raise SystemExit(2) from error

    source = routing_path()
    console.print(
        f"[bold]Routing manifest:[/bold] {source if source else '(none — LiteLLM prefix defaults)'}"
    )

    purposes: dict[str, str] = {}
    if args.task or args.all_tasks:
        from tau2.hyper.task_loader import (
            load_active_hyper_tau_task,
            load_active_hyper_tau_tasks,
        )

        tasks = (
            [load_active_hyper_tau_task(args.task)]
            if args.task
            else load_active_hyper_tau_tasks()
        )
        for task in tasks:
            for model in _hyper_task_menu_models(task):
                purposes.setdefault(model, "Built-agent menu")
            user_llm = getattr(task, "user_llm", None)
            if user_llm:
                purposes.setdefault(user_llm, "User simulator (task)")
        for model, purpose in _model_routing_seat_defaults().items():
            purposes.setdefault(model, purpose)
    else:
        for model, route in routing.models.items():
            purposes[model] = route.purpose or ""

    providers = Table(title="Providers", show_header=True, expand=True)
    for column in ("Provider", "Wire", "Base URL", "Key variable", "Set?"):
        providers.add_column(column, overflow="fold")
    for name in sorted(routing.providers):
        provider = routing.providers[name]
        is_set = bool(os.environ.get(provider.api_key_env))
        providers.add_row(
            name,
            provider.wire,
            provider.base_url,
            provider.api_key_env,
            "[green]yes[/green]" if is_set else "[yellow]no[/yellow]",
        )
    console.print(providers)

    models = Table(title="Models", show_header=True, expand=True)
    for column in (
        "Model id",
        "Provider",
        "Sent upstream as",
        "Key variable",
        "Purpose",
    ):
        models.add_column(column, overflow="fold")
    missing: dict[str, list[str]] = {}
    unrouted: list[str] = []
    for model in sorted(purposes):
        route = routing.resolve(model)
        if route.provider is None:
            unrouted.append(model)
            models.add_row(
                model, "[yellow](unrouted)[/yellow]", model, "-", purposes[model]
            )
            continue
        key_env = route.provider.api_key_env
        if not os.environ.get(key_env):
            missing.setdefault(key_env, []).append(model)
        models.add_row(
            model,
            route.provider.name,
            route.litellm_model,
            key_env if os.environ.get(key_env) else f"[yellow]{key_env}[/yellow]",
            purposes[model],
        )
    console.print(models)

    if unrouted:
        console.print(
            "[yellow]Ids with no manifest entry and no LiteLLM provider prefix "
            "(LiteLLM will reject these):[/yellow] " + ", ".join(unrouted)
        )
        if args.strict:
            raise SystemExit(1)
    if missing:
        console.print("[yellow]Missing API key variables:[/yellow]")
        for key_env in sorted(missing):
            console.print(f"  {key_env}  ← {', '.join(missing[key_env])}")
        console.print(
            "Set them in .env, or edit model_routing.toml to route those models "
            "to a provider whose key you have."
        )
        if args.strict:
            raise SystemExit(1)
    else:
        console.print("[green]Every listed model has its API key variable set.[/green]")
