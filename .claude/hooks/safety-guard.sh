#!/bin/bash
# PreToolUse hook: blocks outbound sends, campaign lifecycle changes and destructive shell commands.
# Exit 0 = allow, exit 2 = block (Claude shows the message and asks the user).
# Trimmed from gtm-os-kit's safety-guard.sh to this repo's stack. Add your own MCP tool names below.
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null)
TOOL_INPUT=$(echo "$INPUT" | jq -c '.tool_input // {}' 2>/dev/null)

block() { echo "SAFETY GUARD BLOCKED: $1"; echo "Tool: $TOOL_NAME"; echo "Details: $(echo "$TOOL_INPUT" | head -c 300)"; echo
          echo "Describe what you were about to do and ask the user for explicit approval."; exit 2; }

# Outbound tools: anything that sends, enrolls, or changes a live campaign. The flywheel is read-only by design.
case "$TOOL_NAME" in
  mcp__getleads__send_contacts_to_heyreach|mcp__getleads__create_heyreach_campaign|mcp__getleads__enrich_heyreach_leads) block "Outbound send" ;;
  mcp__*activate_campaign*|mcp__*pause_campaign*|mcp__*resume_campaign*|mcp__*stop_lead*) block "Campaign lifecycle change" ;;
  mcp__*add_to_campaign*|mcp__*add_leads*|mcp__*bulk_assign*|mcp__*create_campaign*|mcp__*delete_campaign*) block "Campaign mutation" ;;
esac

if [ "$TOOL_NAME" = "Bash" ]; then
  CMD=$(echo "$TOOL_INPUT" | jq -r '.command // ""' 2>/dev/null)
  echo "$CMD" | grep -qE '\bgit\s+push\s+.*(-f|--force)\b'            && block "git push --force"
  echo "$CMD" | grep -qE '\bgit\s+reset\s+--hard\b'                    && block "git reset --hard"
  echo "$CMD" | grep -qE '\brm\s+-(rf|fr)\b'                           && block "rm -rf"
  echo "$CMD" | grep -qiE '\b(DROP\s+(TABLE|DATABASE|SCHEMA)|TRUNCATE\s+TABLE)\b' && block "Destructive SQL"
  echo "$CMD" | grep -qE '(curl|wget)\s.*\|\s*(ba)?sh'                 && block "Remote code piped to shell"
  echo "$CMD" | grep -qE '\brm\s.*\.(env|pem|key|credentials|secret)'  && block "Deleting a secrets file"
  # deepline tools execute on anything that is not a read: the flywheel never writes to a vendor
  echo "$CMD" | grep -qE 'deepline\s+tools\s+execute\s+\S*(add|create|delete|update|activate|pause|resume|send|push|assign)' && block "Vendor write via Deepline"
fi
exit 0
