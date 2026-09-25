import sys
from pathlib import Path
sys.path.insert(0, str(Path('C:/NUS-ISS/tmp/pdfdeps')))
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4

ROOT = Path('C:/NUS-ISS')
OUT = ROOT / 'output/pdf/SMYA_YBQYZYHP_StockPilot_Business_Proposal.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
INK = colors.HexColor('#22231F')
ORANGE = colors.HexColor('#D94F20')
MUTED = colors.HexColor('#62665F')
PALE = colors.HexColor('#F5F4EE')
RULE = colors.HexColor('#DDDFD6')
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Hero', fontName='Helvetica-Bold', fontSize=35, leading=39, textColor=INK, spaceAfter=12))
styles.add(ParagraphStyle(name='Deck', fontName='Helvetica', fontSize=16, leading=22, textColor=INK, spaceAfter=18))
styles.add(ParagraphStyle(name='Label', fontName='Helvetica-Bold', fontSize=9, leading=13, textColor=ORANGE, spaceAfter=9))
styles.add(ParagraphStyle(name='Section', fontName='Helvetica-Bold', fontSize=22, leading=27, textColor=INK, spaceAfter=16))
styles.add(ParagraphStyle(name='Sub', fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=INK, spaceBefore=10, spaceAfter=6))
styles.add(ParagraphStyle(name='Copy', fontName='Helvetica', fontSize=10.2, leading=14, textColor=INK, spaceAfter=8))
styles.add(ParagraphStyle(name='SmallCopy', fontName='Helvetica', fontSize=8.6, leading=12, textColor=MUTED, spaceAfter=6))
styles.add(ParagraphStyle(name='Cell', fontName='Helvetica', fontSize=9.2, leading=13.2, textColor=INK))
styles.add(ParagraphStyle(name='CellHead', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=colors.white))

story=[]
def p(text, style='Copy'):
    return Paragraph(text, styles[style])
def add(text, style='Copy'):
    story.append(p(text, style))
def sub(title, text):
    story.append(KeepTogether([p(title,'Sub'),p(text)]))
def table(headers, rows, widths):
    data=[[p(x,'CellHead') for x in headers]] + [[p(x,'Cell') for x in row] for row in rows]
    t=Table(data,colWidths=widths,hAlign='LEFT',repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),INK),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),11),('RIGHTPADDING',(0,0),(-1,-1),11),
        ('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[PALE,colors.white]),
        ('LINEBELOW',(0,1),(-1,-1),0.4,RULE)]))
    story.append(t)
    story.append(Spacer(1,10))
def newpage(n,title):
    story.append(PageBreak())
    add(n,'Label')
    add(title,'Section')

add('BUSINESS PROPOSAL  /  TEAM YBQYZYHP','Label')
add('StockPilot','Hero')
add('Purchasing intelligence, explained.','Deck')
add('NUS-ISS Show Me Your Agent Hackathon<br/>Powered by AWS | Supported by the Singapore Business Federation (SBF)','SmallCopy')
story.append(Spacer(1,12))
add('01 / THE BUSINESS CASE','Label')
sub('The problem', 'Small retail operators need to decide what to reorder, how much to buy and which supplier can deliver in time. When sales history, inventory and supplier terms are reviewed separately, purchasing staff must reconcile them manually. A low unit price can hide a late delivery, while a large precautionary order can tie up cash. Managers need a clear basis for approving the final purchase.')
sub('Our proposal', 'StockPilot brings these decisions into one explainable purchasing workspace. It uses sales and inventory CSVs to forecast demand, flag projected shortages, compare supplier allocations and prepare purchase-order drafts for human review. The initial use case is a small catalogue of 10-15 products, demonstrated with 12 products and three simulated approved suppliers.')
sub('Value to the business', 'The intended benefits are faster preparation, earlier visibility of stock gaps and better cost-versus-delivery decisions. Every recommendation should answer four questions: why this quantity, why these suppliers, what could break the plan and who reviewed it. These benefits are hypotheses for a pilot; commercial savings and real-store outcomes have not been established.')
table(['Primary users','Proposed buyer'],[
    ['Purchasing staff and owner-operators preparing replenishment decisions.','The owner or operations manager of a small retail business.']
],[249,249])
add('<b>Submitted by Team Skibidi Slicers</b><br/>Chia Chong En | Mohd Arif Fiqry Bin Mohd Suffian<br/>Tan Kai Hao Gerald | Trevis Tan','SmallCopy')
add('25 September 2026 | Team code: YBQYZYHP','SmallCopy')

newpage('02 / SOLUTION & DIFFERENTIATION','From stock data to a reviewable order')
add('StockPilot connects the purchasing workflow while keeping calculations inspectable and the approval decision with a person.')
table(['Workflow','What StockPilot does','Business purpose'],[
    ['1. Prepare data','Validate sales and inventory CSVs; retain a clearly labelled sample option.','Start from consistent inputs and surface data gaps.'],
    ['2. Anticipate demand','Forecast 14 days using recent weekday patterns; show stock coverage and owner-entered adjustments.','Identify products needing intervention before a purchase is drafted.'],
    ['3. Compare sourcing','Evaluate one- or two-supplier allocations against delivery timing, price, quantity and eligibility constraints.','Explain the trade-off between early availability and purchasing cost.'],
    ['4. Check resilience','Replay the proposed allocation under higher demand or delayed new deliveries.','Expose assumptions that could make the plan fail.'],
    ['5. Review and record','Apply a shared-budget draft gate, persist order details and support simulated manager review and exports.','Provide a reviewable decision and a record of the approved simulation.']
],[91,223,184])
sub('A bounded agent with evidence', 'The optional AI briefing follows a controlled sequence: read inventory, read recommendations, check budget, then explain the results. Python performs forecasting, purchasing arithmetic and constraint checks independently. The model has no approval or dispatch tool. Live organiser-gateway connectivity remains unverified.')
sub('Why this approach is useful', 'The proposition combines demand, delivery timing, sourcing and review in one small workflow. A recommendation includes its assumptions and blocked conditions, rather than a quantity alone. Compared with the proposed manual-workflow baseline, the pilot will test whether this improves preparation time and decision quality; no claim of competitor superiority is made.')
add('<b>Current boundary:</b> Supplier data and manager roles are simulated. The prototype does not send orders or emails, reserve inventory or confirm incoming stock after approval.','SmallCopy')

newpage('03 / ADOPTION & COMMERCIAL MODEL','Start with a focused retail pilot')
sub('Initial customer profile', 'Recruit small retailers with repeat purchasing, accessible daily sales exports and a manager able to review recommendations. Begin with 10-15 regularly traded products, where stock records and supplier lead times can be checked. This is a proposed beachhead, not a validated market-size estimate or a claim of customer demand.')
sub('Route to adoption', 'Use a short workflow demonstration to recruit a small pilot cohort through direct retailer outreach and relevant business networks. Collect the current purchasing process, then run StockPilot alongside it. Start in shadow mode: staff compare the recommendations with their usual decisions while normal purchasing controls remain in place. No pilot partners or distribution agreements are currently claimed.')
table(['Commercial hypothesis','How to validate it'],[
    ['A subscription per store or small catalogue, with optional paid onboarding.','Interview owners about willingness to pay after demonstrating a useful, repeatable workflow. Set pricing only after validating value and support effort.'],
    ['CSV-based onboarding reduces the initial integration burden.','Record time spent mapping exports, correcting inventory and maintaining supplier data.'],
    ['Explainability and human review support repeat use.','Track weekly usage, overrides, rejected drafts and the reasons managers accept or reject recommendations.']
],[220,278])
sub('Illustrative customer economics', 'For planning only, assume 20 purchasing cycles per month, 15 minutes saved per cycle and staff time valued at S$20 per hour. The implied time value is <b>20 x 15 / 60 x S$20 = S$100 per month</b>. This is an assumption-based illustration, not a measured saving or necessarily a cash reduction. Purchasing savings should be counted separately only when service outcomes remain comparable.')
sub('Delivery cost and sustainability', 'The main cost drivers are hosting, model requests, onboarding, data cleanup and ongoing support. The core calculation workflow runs without an API key; AI briefings are optional and bounded to a short sequence. During the pilot, record actual usage and support effort before setting a price or projecting margins. AWS hosting is a proposed delivery option; deployment evidence is a separate submission item.')

newpage('04 / SUCCESS MEASURES','Test value before claiming impact')
add('The numerical targets below are proposed acceptance goals inherited from the project scope. They are not achieved outcomes. Baselines, sample size and observation periods should be agreed before the pilot begins.')
table(['Measure / proposed target','Measurement approach'],[
    ['Preparation time<br/><b>Under 5 minutes per agreed batch</b>','Time a person from validated inputs to a review-ready draft. Record data cleanup separately and compare with the existing workflow on similar batches.'],
    ['Forecast error<br/><b>Aggregate WAPE below 20%</b>','Use held-out sales dates with training restricted to earlier dates. Compare weekday averages, last-week forecasts and moving averages; also report per-product MAE and nonzero-actual MAPE.'],
    ['Early warning<br/><b>7 days where observable</b>','Record when a projected shortage is first flagged and the eventual shortage date. Report missed and false alerts. Seven days is a target, not a guarantee when inputs arrive late.'],
    ['Purchasing cost<br/><b>5-10% reduction hypothesis</b>','Compare cost with the cheapest feasible single-supplier plan under the same constraints. Report service outcomes alongside cost; do not claim savings when no comparable feasible plan exists.'],
    ['Review and adoption<br/><b>Track throughout the pilot</b>','Record draft completion, manager decisions, overrides, stockout days and unmet units. Use these to detect faster but poorer decisions.']
],[192,306])
sub('What the prototype can evaluate now', 'The offline evaluator uses a final 14-day holdout and at least 42 consecutive daily observations. It compares three forecast methods and replays purchasing against a reorder-point baseline. The bundled data contains 84 synthetic daily observations for each of 12 products. This supports reproducible demonstrations, not claims about current Singapore retail demand.')
sub('Fair interpretation', 'The reorder-point replay and StockPilot may deliver different service levels, so lower simulated cost alone does not establish a benefit. Calculation runtime is also different from human preparation time. No numerical evaluation result or real-store improvement is claimed in this proposal.')

newpage('05 / DELIVERY PLAN & READINESS','A clear path from demo to pilot')
table(['Proposed stage','Exit condition'],[
    ['1. Harden the prototype','Resolve the known calculation findings, validate urgent-order comparisons and rehearse the complete review workflow.'],
    ['2. Establish a baseline','Agree the pilot catalogue, verify inventory and supplier assumptions, document the current process and define success measures.'],
    ['3. Run in shadow mode','Compare recommendations with ordinary decisions, record manager feedback and evaluate time, cost and service together.'],
    ['4. Decide on a controlled pilot','Proceed only after correcting material issues, validating value and adding authenticated access, reliable operations and order reconciliation.']
],[158,340])
sub('Current delivery evidence', 'The repository documents CSV validation, catalogue analysis, forecasting, supplier splitting, budget checks, disruption scenarios, persisted drafts, simulated review and exports. Offline evaluation and mocked gateway integration are included. This is a hackathon prototype, not a production-readiness certification.')
sub('Material limitations to resolve', 'Three calculation findings remain open: percentage rounding may overstate demand; supplier comparison may omit an urgent deadline; and one zero-quantity conflict message may misidentify incoming stock as the cause. Real supplier behaviour, authenticated approvals, overlapping-order reconciliation and catalogue scaling require further work.')
sub('Hosting and pilot readiness', 'Live gateway connectivity and AWS deployment are unverified in the reviewed documentation. A hosted pilot needs access controls, HTTPS, backups, monitoring and an operating owner. Supplier dispatch is outside the prototype scope.')
sub('The proposed next step', 'Seek retailer pilot participation and feedback to establish measurable value before investing in deeper integrations or commercial rollout.')
add('PROJECT BASIS & REFERENCES','Label')
add('Repository: <link href="https://github.com/xensica/nus-iss" color="#D94F20">github.com/xensica/nus-iss</link><br/>Project and purchase_demo READMEs: features, evaluation and limitations. Purchasing-agent requirements: intended scope; older status labels are superseded by the current application guide.<br/>Commercial model, economics and rollout are planning assumptions, not achieved results.','SmallCopy')

def decorate(c,doc):
    w,h=A4
    c.setFillColor(ORANGE)
    c.rect(0,h-9,w,9,fill=1,stroke=0)
    c.setFont('Helvetica-Bold',8)
    c.setFillColor(MUTED)
    c.drawString(48,h-35,'STOCKPILOT / BUSINESS PROPOSAL')
    c.drawRightString(w-48,h-35,'SKIBIDI SLICERS')
    c.setStrokeColor(RULE)
    c.line(48,43,w-48,43)
    c.setFont('Helvetica',8)
    c.drawString(48,29,'SMYA FINAL SUBMISSION | YBQYZYHP')
    c.drawRightString(w-48,29,f'{doc.page} / 5')

doc=SimpleDocTemplate(str(OUT),pagesize=A4,rightMargin=48,leftMargin=48,topMargin=62,bottomMargin=57,
                      title='StockPilot - Business Proposal - YBQYZYHP',author='Team Skibidi Slicers',
                      subject='NUS-ISS Show Me Your Agent Hackathon final submission')
doc.build(story,onFirstPage=decorate,onLaterPages=decorate)

import fitz
from pypdf import PdfReader
reader=PdfReader(str(OUT))
assert len(reader.pages)==5, f'Expected 5 pages, got {len(reader.pages)}'
text='\n'.join(page.extract_text() for page in reader.pages)
for required in ['YBQYZYHP','Mohd Arif Fiqry Bin Mohd Suffian','5-10%','calculation findings']:
    assert required in text, required
pdf=fitz.open(OUT)
renderdir=ROOT/'tmp/pdfs/rendered'
renderdir.mkdir(parents=True,exist_ok=True)
for i,page in enumerate(pdf):
    page.get_pixmap(matrix=fitz.Matrix(1.35,1.35)).save(renderdir/f'proposal-{i+1}.png')
print(f'Created {OUT}; {len(reader.pages)} pages; {OUT.stat().st_size:,} bytes')
