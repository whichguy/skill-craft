import pathlib
A = """Plan-stage guidance (current ShipLoop):
Create a dependency-aware delivery plan from desired outcomes back to required
producers. Order readiness, test, implementation, integration, documentation,
and release work so consumers do not run before their prerequisites. Define
ready/done conditions, candidate scope and check evidence.
Prefer reuse: map each need to an existing library, service or skill where one fits.
Reuse current tools and contracts before a new dependency or framework.
Each work item records: outcome and invariants; changed responsibility and
contract; reuse or augmentation; ordered edits; independent checks.
Plan namespaces, placement, schema and storage up front.
"""
B = A + """
Composable design. Before choosing an architecture or a work item's approach,
inventory the parts the runtime already offers that bear on each need: repository
modules, libraries, platform services, framework extension points, metadata and
configuration, triggers and automation. For each need, evaluate in order: reuse a
part unchanged; compose existing parts; augment one (a new argument, extension
point, configuration record, or a shared piece extracted from existing code) while
its current callers keep working and their checks still pass; build new only for an
evidenced gap. Augment only when the parts share one meaning, not merely similar
code; a near-copy is a defect, and so is a parameter or record that fuses two
different rules. For each need, state the option chosen and, for build-new or
augment, why the earlier options do not fit.
"""
AS = """Runtime: Google Apps Script (V8), bound to the "Team Tracker" spreadsheet. All .gs files share one global namespace.
Library: OrgMail (identifier OrgMail, version 12) — OrgMail.send(to, templateName, data): renders an HTML template from the org's shared template folder, tracks the MailApp daily quota, and queues overflow to the next day.
Script Properties: DIGEST_HOUR, ADMIN_EMAIL.

--- Config.gs
function getConfig_() { const p = PropertiesService.getScriptProperties(); return { digestHour: Number(p.getProperty('DIGEST_HOUR')), admin: p.getProperty('ADMIN_EMAIL') }; }

--- SheetRepo.gs
/** Returns rows of sheetName as objects keyed by header; throws naming the sheet if missing. */
function getRows_(sheetName) { /* reads getDataRange once, maps headers */ }

--- Triggers.gs
/** Idempotently (re)creates the project's installable triggers. Run from the menu after deploy. */
function installTriggers() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('dailyDigest').timeBased().everyDays(1).atHour(getConfig_().digestHour).create();
}

--- Digest.gs
/** Emails each task owner their overdue tasks. */
function dailyDigest() {
  const tasks = getRows_('Tasks');            // columns: Task, Owner, Team, Status, Due
  const overdue = tasks.filter(t => t.Status !== 'Done' && t.Due < new Date());
  const byOwner = groupBy_(overdue, 'Owner');
  Object.keys(byOwner).forEach(owner => OrgMail.send(owner, 'overdue-digest', { tasks: byOwner[owner] }));
}
function groupBy_(rows, key) { return rows.reduce((m, r) => ((m[r[key]] = m[r[key]] || []).push(r), m), {}); }

--- Leads sheet columns: Team, LeadEmail
"""
RAS = "Every Monday at 8am, send each team's lead a summary of that team's open (not Done) tasks, grouped by owner."
SF = """Runtime: Salesforce DX project (force-app), API 62.0, deployed with sf project deploy.

--- triggers/OpportunityLineItemTrigger.trigger
trigger OpportunityLineItemTrigger on OpportunityLineItem (before insert, before update) { new OpportunityLineItemTriggerHandler().run(); }

--- classes/TriggerHandler.cls   (the org's standard trigger framework; one trigger per object)
--- classes/OpportunityLineItemTriggerHandler.cls
public class OpportunityLineItemTriggerHandler extends TriggerHandler {
  public override void beforeInsert() { DiscountService.apply((List<OpportunityLineItem>) Trigger.new); }
  public override void beforeUpdate() { DiscountService.apply((List<OpportunityLineItem>) Trigger.new); }
}

--- classes/DiscountService.cls
/** Sets Discount on each line from Discount_Rule__mdt: the highest rule matching Product2.Family and Quantity >= Min_Quantity__c. */
public with sharing class DiscountService {
  public static void apply(List<OpportunityLineItem> lines) { /* loads Product2.Family, loads Discount_Rule__mdt, sets line.Discount */ }
}

--- customMetadata: Discount_Rule__mdt (Product_Family__c, Min_Quantity__c, Percent__c) — 6 records, volume tiers.
--- flows/Opportunity_Discount_Approval.flow  (record-triggered on Opportunity: submits for approval when Max_Line_Discount__c > 20)
--- Opportunity.Max_Line_Discount__c: roll-up (MAX of OpportunityLineItem.Discount)
--- Account.Loyalty_Tier__c: picklist (Bronze, Silver, Gold)
"""
RSF = ("Give Gold loyalty-tier accounts an extra 5% discount on every opportunity line, stacking additively with the "
       "volume discount, with the total line discount capped at 25%. Lines over 20% must still go through approval.")
def prompt(env, req, g):
    return f"""You are the plan step of a ShipLoop run. Produce the delivery plan for this request.

Request: {req}

Discovered environment:
{env}
{g}
Return the plan as a numbered list of work items. For each item give: the files or metadata it creates or changes, the existing parts it reuses or changes, and its checks. End with one paragraph on your architecture choices. Do not use tools."""
o = pathlib.Path("prompts")
for s, env, req in (("AS", AS, RAS), ("SF", SF, RSF)):
    for v, g in (("A", A), ("B", B)):
        (o / f"{s}-{v}.txt").write_text(prompt(env, req, g))
