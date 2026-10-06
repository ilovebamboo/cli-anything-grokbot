#!/usr/bin/env python3
"""CLI harness for the installed Grok Bot desktop app.

Usage:
    cli-anything-grokbot --json app info
    cli-anything-grokbot --json app status
    cli-anything-grokbot app open
    cli-anything-grokbot
"""

from __future__ import annotations

import json
import shlex

import click

from cli_anything.grokbot.utils.cdp import ControlError
from cli_anything.grokbot.utils.chat_control import ChatControl, control_lock

from cli_anything.grokbot.utils.grokbot_backend import app_focus, app_info, app_open, app_status
from cli_anything.grokbot.utils.repl_skin import ReplSkin

_json_output = False
_repl_mode = False


def output(data: dict) -> None:
    if _json_output:
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return
    for key, value in data.items():
        click.echo(f"{key}: {value}")


@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, help="Output JSON")
@click.pass_context
def cli(ctx: click.Context, use_json: bool) -> None:
    """Control Grok Bot, including bot/group chats via local Electron CDP."""
    global _json_output
    _json_output = use_json
    ctx.ensure_object(dict)
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


@cli.group()
def app() -> None:
    """Inspect, open, and focus the real Grok Bot app."""


@app.command("info")
def app_info_cmd() -> None:
    """Read identity from the installed app bundle."""
    output(app_info())


@app.command("status")
def app_status_cmd() -> None:
    """Show whether the installed app is running."""
    output(app_status())


@app.command("open")
def app_open_cmd() -> None:
    """Bring up the real Grok Bot app with open -a."""
    output(app_open())


@app.command("focus")
def app_focus_cmd() -> None:
    """Activate the real Grok Bot app."""
    result = app_focus()
    output(result)
    if not result.get("verified"):
        raise SystemExit(4)


@app.command('connect')
@click.option('--restart', is_flag=True, help='Allow a graceful Grok Bot restart if CDP is not enabled.')
@click.option('--port', default=9337, type=click.IntRange(1024,65535))
def app_connect_cmd(restart, port):
    """Check or enable a localhost-only Electron debugging connection."""
    from cli_anything.grokbot.utils.connection import connect_app
    with control_lock():
        output(connect_app(port, restart))


@cli.group()
@click.option('--port', default=9337, type=click.IntRange(1024,65535), envvar='GROKBOT_CDP_PORT')
@click.pass_context
def chat(ctx, port):
    """Read, open and message bot/group chats. No OCR or desktop clicks."""
    ctx.obj['port'] = port


def chat_run(ctx, method, *args, **kwargs):
    with control_lock(), ChatControl(ctx.obj['port']) as controller:
        output(getattr(controller, method)(*args, **kwargs))


@chat.command('list')
@click.pass_context
def chat_list(ctx):
    """List rendered sidebar chats with stable IDs and bot/group kinds."""
    chat_run(ctx, 'list')


@chat.command('open')
@click.argument('target')
@click.pass_context
def chat_open(ctx, target):
    """Open an exact name or ID and verify both active ID and heading."""
    chat_run(ctx, 'open', target)


@chat.command('read')
@click.option('--to', 'target')
@click.option('--limit', default=20, type=click.IntRange(1,500))
@click.option('--latest', is_flag=True, help='Scroll transcript to the latest messages.')
@click.pass_context
def chat_read(ctx, target, limit, latest):
    """Read rendered messages, roles and sequences; not complete history."""
    chat_run(ctx, 'read', target, limit, latest)


@chat.command('send')
@click.option('--to', 'target', required=True)
@click.option('--text')
@click.option('--text-file', type=click.File('r', encoding='utf-8'), help='UTF-8 file or - for stdin.')
@click.option('--send', 'deliver', is_flag=True, help='Actually send; default is a read-only dry-run.')
@click.option('--request-id', help='Stable caller ID; prevents duplicate sends on retries.')
@click.option('--timeout', default=20, type=click.IntRange(1,120))
@click.pass_context
def chat_send(ctx, target, text, text_file, deliver, request_id, timeout):
    """Send text through the real app, protect drafts, verify transcript echo."""
    if (text is None) == (text_file is None):
        raise ControlError('Provide exactly one of --text or --text-file')
    body = text if text is not None else text_file.read(20001)
    chat_run(ctx, 'send', target, body, deliver, request_id, timeout)


@chat.command('wait')
@click.option('--to', 'target', required=True)
@click.option('--after', type=click.IntRange(0), required=True, help='User message sequence returned by send.')
@click.option('--timeout', default=30, type=click.IntRange(1,300))
@click.pass_context
def chat_wait(ctx, target, after, timeout):
    """Wait for assistant text after a sequence (not proof of task completion)."""
    chat_run(ctx, 'wait_reply', target, after, timeout)


@cli.group()
@click.option('--port', default=9337, type=click.IntRange(1024,65535), envvar='GROKBOT_CDP_PORT')
@click.pass_context
def bot(ctx, port):
    """Inspect/create/update/delete individual Bots; guarded, dry-run by default."""
    ctx.obj['port']=port


def bot_run(ctx, method, *args, **kwargs):
    from cli_anything.grokbot.utils.bot_control import BotControl
    with control_lock(), BotControl(ctx.obj['port']) as controller:
        output(getattr(controller, method)(*args, **kwargs))


@bot.command('list')
@click.pass_context
def bot_list(ctx):
    """Read app-client roster including hidden Bots and protected IDs."""
    bot_run(ctx, 'list')


@bot.command('info')
@click.argument('target')
@click.pass_context
def bot_info(ctx, target):
    """Read profile and running/ownership state by exact ID or name."""
    bot_run(ctx, 'info', target)


def profile_options(fn):
    for option in [click.option('--name'),click.option('--description'),
                   click.option('--description-file',type=click.File('r',encoding='utf-8')),
                   click.option('--title',help='Profile label, not a system prompt/model selection.'),
                   click.option('--apply',is_flag=True,help='Perform mutation; default is dry-run.'),
                   click.option('--request-id',help='Required with --apply; stable local retry ID.')]:
        fn=option(fn)
    return fn


def read_profile(name, description, description_file, title, create=False):
    from cli_anything.grokbot.utils.bot_control import profile_fields
    if description is not None and description_file is not None:
        raise ControlError('Use --description OR --description-file')
    if description_file is not None:description=description_file.read(20001)
    return profile_fields(name, description, title, create=create)


@bot.command('create')
@profile_options
@click.pass_context
def bot_create(ctx,name,description,description_file,title,apply,request_id):
    """Create a new personal Bot (not a group); no first task sent."""
    bot_run(ctx,'mutate','create',profile=read_profile(name,description,description_file,title,True),
            apply=apply,request_id=request_id)


@bot.command('update')
@click.option('--id','bot_id',required=True,help='Exact Bot UUID; names are not accepted.')
@profile_options
@click.pass_context
def bot_update(ctx,bot_id,name,description,description_file,title,apply,request_id):
    """Update name/description/title only; leave unspecified fields unchanged."""
    bot_run(ctx,'mutate','update',bot_id=bot_id,
            profile=read_profile(name,description,description_file,title),apply=apply,request_id=request_id)


@bot.command('delete')
@click.option('--id','bot_id',required=True,help='Exact Bot UUID; single-target only.')
@click.option('--confirm-name',help='Must match current raw Bot name from bot info.')
@click.option('--confirm-delete',is_flag=True,help='Acknowledge deletion may remove chat history.')
@click.option('--apply',is_flag=True,help='Actually delete; default is dry-run.')
@click.option('--request-id',help='Required with --apply.')
@click.pass_context
def bot_delete(ctx,bot_id,confirm_name,confirm_delete,apply,request_id):
    """Delete an idle personal Bot; refuses main/system/shared/group-member Bots."""
    bot_run(ctx,'mutate','delete',bot_id=bot_id,confirm_name=confirm_name,
            confirm_delete=confirm_delete,apply=apply,request_id=request_id)


@cli.command()
def repl() -> None:
    """Interactive session. Empty input shows help."""
    global _repl_mode
    _repl_mode = True
    skin = ReplSkin("grokbot", version="1.2.1")
    skin.print_banner()
    commands = {
        "info": "Read the installed app identity",
        "status": "Show running state",
        "open": "Launch or focus Grok Bot",
        "focus": "Activate Grok Bot",
        "bot list": "Read Bot profiles and ownership",
        "bot create --help": "Guarded create/update/delete (default dry-run)",
        "chat list": "List bot/group chats",
        "chat read --latest": "Read latest rendered messages",
        "chat send --help": "See guarded message delivery options",
        "help": "Show commands",
        "quit": "Exit",
    }
    session = skin.create_prompt_session()
    while True:
        try:
            line = skin.get_input(session, project_name="Grok Bot").strip()
        except (EOFError, KeyboardInterrupt):
            skin.print_goodbye()
            return
        if not line or line == "help":
            skin.help(commands)
            continue
        if line in {"quit", "exit"}:
            skin.print_goodbye()
            return
        try:
            if line == "info":
                output(app_info())
            elif line == "status":
                output(app_status())
            elif line == "open":
                output(app_open())
            elif line == "focus":
                output(app_focus())
            elif line.startswith(('chat ', 'bot ')):
                cli.main(args=shlex.split(line), standalone_mode=False)
            else:
                skin.error(f"unknown command: {line}")
        except Exception as exc:
            skin.error(str(exc))


def main() -> None:
    try:
        cli()
    except ControlError as exc:
        if _json_output:
            click.echo(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        else:
            click.echo(f'Error: {exc}', err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
