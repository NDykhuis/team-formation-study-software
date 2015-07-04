# This file generates some basic, fairly smart agents to seed the evolutionary simulation

outfile = 'customagenttable.csv'

columnorder = ['uuid', 'condition', 'apply_nohist', 'apply_deltapay_intercept', 'apply_deltapay_slope', 'apply_deltapay_aic', 'apply_pastcontrib_intercept', 'apply_pastcontrib_slope', 'apply_pastcontrib_slope_pay', 'apply_pastcontrib_aic', 'acceptvote_nohist', 'acceptvote_noaccept', 'acceptvote_stayaccept', 'acceptvote_deltapay_intercept', 'acceptvote_deltapay_slope', 'acceptvote_deltapay_aic', 'acceptvote_globalrtg_intercept', 'acceptvote_globalrtg_slope', 'acceptvote_globalrtg_slope_pay', 'acceptvote_globalrtg_aic', 'acceptvote_pastcontrib_intercept', 'acceptvote_pastcontrib_slope', 'acceptvote_pastcontrib_slope_pay', 'acceptvote_pastcontrib_aic', 'join_nohist', 'join_deltapay_intercept', 'join_deltapay_stay', 'join_deltapay_slope', 'join_deltapay_aic', 'join_globalrtg_intercept', 'join_globalrtg_stay', 'join_globalrtg_slope', 'join_globalrtg_slope_pay', 'join_globalrtg_aic', 'pubgood_contrib_pastcontrib_intercept', 'pubgood_contrib_pastcontrib_slope', 'pubgood_contrib_pastcontrib_stderr', 'pubgood_contrib_pastcontrib_r2', 'pubgood_contrib_globalrtg_intercept', 'pubgood_contrib_globalrtg_slope', 'pubgood_contrib_globalrtg_r2', 'pubgood_contrib_globalrtg_stderr', 'pubgood_avgcontrib', 'pubgood_sdcontrib', 'pubgood_rating_contrib_intercept', 'pubgood_rating_contrib_slope', 'pubgood_rating_contrib_stderr', 'pubgood_rating_contrib_r2', 'pubgood_ratings_per_round', 'pubgood_ratings_per_round_sd', 'pubgood_prop_rounds_nrats_0', 'pubgood_pct1', 'pubgood_pct2', 'pubgood_pct3', 'pubgood_pct4', 'pubgood_pct5', 'apply_time_q1', 'acceptvote_time_q1', 'join_time_q1', 'pubgood_time_q1', 'apply_time_med', 'acceptvote_time_med', 'join_time_med', 'pubgood_time_med', 'apply_time_q3', 'acceptvote_time_q3', 'join_time_q3', 'pubgood_time_q3']

defaultdict = {
  'uuid': None,
  'condition': None,  # Always apply to everything
  'apply_nohist': 1.0,
  'apply_deltapay_intercept': 1,
  'apply_deltapay_slope': 0.5,
  'apply_deltapay_aic': 1,
  'apply_pastcontrib_intercept': 1,
  'apply_pastcontrib_slope': 0.5,
  'apply_pastcontrib_slope_pay': 0.5,
  'apply_pastcontrib_aic': 1,
  # Accept anything in absence of other info
  # Otherwise, accept conditionally
  'acceptvote_nohist': 1,
  'acceptvote_noaccept': 0,
  'acceptvote_stayaccept': 0,
  'acceptvote_deltapay_intercept': 0,
  'acceptvote_deltapay_slope': 1,
  'acceptvote_deltapay_aic': 1,
  'acceptvote_globalrtg_intercept': -3,
  'acceptvote_globalrtg_slope': 1,
  'acceptvote_globalrtg_slope_pay': 0.2,
  'acceptvote_globalrtg_aic': 1,
  'acceptvote_pastcontrib_intercept': -0.5,
  'acceptvote_pastcontrib_slope': 2,
  'acceptvote_pastcontrib_slope_pay': 0.1,
  'acceptvote_pastcontrib_aic': 1,
  # Join should be focused on deltapay
  # These numbers are assigned somewhat randomly
  'join_nohist': 0.5,
  'join_deltapay_intercept': -2,
  'join_deltapay_stay': 0.5,
  'join_deltapay_slope': 1,
  'join_deltapay_aic': 1,
  'join_globalrtg_intercept': -3,
  'join_globalrtg_stay': 0.5,
  'join_globalrtg_slope': 1,
  'join_globalrtg_slope_pay': 0.25,
  'join_globalrtg_aic': 1,
  # Contribs are high by default, but conditional
  'pubgood_contrib_pastcontrib_intercept': 0,
  'pubgood_contrib_pastcontrib_slope': 1,
  'pubgood_contrib_pastcontrib_stderr': 0.1,
  'pubgood_contrib_pastcontrib_r2': 1,
  'pubgood_contrib_globalrtg_intercept': -0.25,
  'pubgood_contrib_globalrtg_slope': 0.25,
  'pubgood_contrib_globalrtg_r2': 1,
  'pubgood_contrib_globalrtg_stderr': 0.1,
  'pubgood_avgcontrib': 0.75,
  'pubgood_sdcontrib': 0.1,
  # Assign honest ratings
  'pubgood_rating_contrib_intercept': 1,
  'pubgood_rating_contrib_slope': 4,
  'pubgood_rating_contrib_stderr': 0,
  'pubgood_rating_contrib_r2': 1,
  'pubgood_ratings_per_round': 2,
  'pubgood_ratings_per_round_sd': 1,
  'pubgood_prop_rounds_nrats_0': 0,
  # The following should not be used
  'pubgood_pct1': 0.2,
  'pubgood_pct2': 0.2,
  'pubgood_pct3': 0.2,
  'pubgood_pct4': 0.2,
  'pubgood_pct5': 0.2,
  'apply_time_q1': 0,
  'acceptvote_time_q1': 0,
  'join_time_q1': 0,
  'pubgood_time_q1': 0,
  'apply_time_med': 0,
  'acceptvote_time_med': 0,
  'join_time_med': 0,
  'pubgood_time_med': 0,
  'apply_time_q3': 0,
  'acceptvote_time_q3': 0,
  'join_time_q3': 0,
  'pubgood_time_q3': 0
}

#permutations = {
#  'condition':['public','private','varmult']
#  'apply_nohist':[],
#}

# For all permutations, generate an agent by modifying defaultdict
# Or maybe we could just put these lists inside defaultdict

# Then, for column name in columnorder, create a line of csv file

rows = []

# Add header
#rows = [ ','.join(columnorder) ]

def make3conds(agentdict, agentname):
  rows = []
  for cond in ['public', 'private', 'varmult']:
    agentdict['condition'] = cond
    agentdict['uuid'] = agentname+cond
    row = ','.join([str(agentdict[colname]) for colname in columnorder])
    rows.append(row)
  return rows
    


# For now, just dump this agent
# to stdout, where we can copy it into the file.
vanilla = defaultdict.copy()
vanilla['uuid'] = 'vanilla'
rows.extend(make3conds(vanilla, 'vanilla'))

mean = defaultdict.copy()
mean['uuid'] = 'mean'
mean['pubgood_avgcontrib'] = 0.0
mean['pubgood_sdcontrib'] = 0.0
mean['pubgood_contrib_pastcontrib_intercept'] = 0.0
mean['pubgood_contrib_pastcontrib_slope'] = 0.0
mean['pubgood_contrib_pastcontrib_stderr'] = 0.0
mean['pubgood_contrib_pastcontrib_r2'] = 0
mean['pubgood_contrib_globalrtg_intercept'] = 0.0
mean['pubgood_contrib_globalrtg_slope'] = 0.0
mean['pubgood_contrib_globalrtg_r2'] = 0
mean['pubgood_contrib_globalrtg_stderr'] = 0.0
rows.extend(make3conds(mean, 'mean'))

nice = defaultdict.copy()
nice['uuid'] = 'nice'
nice['pubgood_avgcontrib'] = 1.0
nice['pubgood_sdcontrib'] = 0.0
nice['pubgood_contrib_pastcontrib_intercept'] = 1.0
nice['pubgood_contrib_pastcontrib_slope'] = 0.0
nice['pubgood_contrib_pastcontrib_stderr'] = 0.0
nice['pubgood_contrib_pastcontrib_r2'] = 0
nice['pubgood_contrib_globalrtg_intercept'] = 1.0
nice['pubgood_contrib_globalrtg_slope'] = 0.0
nice['pubgood_contrib_globalrtg_r2'] = 0
nice['pubgood_contrib_globalrtg_stderr'] = 0.0
rows.extend(make3conds(nice, 'nice'))

random = defaultdict.copy()
random['uuid'] = 'random'
random.update( {
  'pubgood_avgcontrib': 0.5,
  'pubgood_sdcontrib': 0.4,
  'pubgood_contrib_pastcontrib_intercept': 0.5,
  'pubgood_contrib_pastcontrib_slope': 0.0,
  'pubgood_contrib_pastcontrib_stderr': 0.4,
  'pubgood_contrib_pastcontrib_r2': 0,
  'pubgood_contrib_globalrtg_intercept': 0.5,
  'pubgood_contrib_globalrtg_slope': 0.0,
  'pubgood_contrib_globalrtg_r2': 0,
  'pubgood_contrib_globalrtg_stderr': 0.4
  } )
rows.extend(make3conds(random, 'random'))

#grim = defaultdict.copy()
#grim['uuid'] = 'grim'
### TODO: Adjust these for LOG ODDS
#grim.update( {
  #'apply_pastcontrib_intercept': 0,
  #'apply_pastcontrib_slope': 1,
  #'apply_pastcontrib_slope_pay': 0,
  #'apply_pastcontrib_aic': 1,
  #'acceptvote_pastcontrib_intercept': 0,
  #'acceptvote_pastcontrib_slope': 1,
  #'acceptvote_pastcontrib_slope_pay': 0,
  #'acceptvote_pastcontrib_aic': 1,
  #} )
#rows.append(make3conds(grim, 'grim'))

for row in rows:
  print row