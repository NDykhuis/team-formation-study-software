library("RSQLite")
library(ggplot2)
library(reshape2)
library(dplyr)
library(lattice)

# source('simhumans_tablegen.R', echo=TRUE)

## UTILITY FUNCTIONS

# Fix R console width (number of columns)
fixwid <- function(howWide=Sys.getenv("COLUMNS")) {options(width=as.integer(howWide))}
r2 <- function(number) { sprintf('%02d',number) }

# Bin contributions
bincontribs <- function(data) {
  bins <- c(-0.01,.125,0.375,0.625,0.875,1)
  ndata <- cut(data, breaks=bins, labels=c(0:4/4))
  ndata <- factor(ndata, c(-1, levels(ndata)), ordered=TRUE)
  ndata[is.na(ndata)] = -1    # Hack!
  ndata
}

namean <- function(x){mean(x, na.rm=TRUE)}
tryna <- function(expr) {tryCatch(expr, error=function(err) NA)}

logoddstoprob <- function(logodds) { exp(logodds)/(1+exp(logodds)) }


# DATA FILE HERE
dbfile = 'simlog_EXPR1_03-31-15.db' 
expr_condition = 'compare'          ## private or public

dbfileprefix = substr(dbfile, 1, nchar(dbfile)-3)

 
 
## DATA IMPORT

drv <- dbDriver("SQLite")
con <- dbConnect(drv, dbfile)

badses <- c(3,6,7,8,12)

sc <- dbGetQuery(con, "SELECT * FROM session_config")
ses_cond_tab <- c('private', 'public')[sc$show_global_ratings+1]
names(ses_cond_tab) <- sc$sessionid

gettable <- function(tablename) {
  temp <- dbGetQuery(con, paste("SELECT * FROM", tablename))
  if ('sessionid' %in% names(temp)) {
    temp <- subset(temp, !(sessionid %in% badses))
    temp$condition <- ses_cond_tab[temp$sessionid]
  }
  temp
}
adduuid <- function(data) {
  data$uuid <- with(data, paste(r2(sessionid), userid, sep='.'))
  data
}
steporder <- c('apply', 'acceptvote', 'join', 'pubgood', 'pg_postprocess')
fixetype <- function(data) {
  data$eventtype <- factor(data$eventtype, levels=steporder, ordered=TRUE)
  data
}

#goodses = paste('(',paste(goodsessions,sep=','),',')
intr <- adduuid(gettable("introresponses"))
tfl <- fixetype(adduuid(gettable("tflog")))
tfe <- fixetype(adduuid(gettable("tfevent")))
tfe$elapsed <- tfe$etime - tfe$stime
rs <- adduuid(gettable("ratingstatus"))
grat <- adduuid(gettable("globalratings"))
#fp <- adduuid(gettable("finalpay"))
#fp$paydollars <- ceiling(fp$pay/fp$exchange_rate)
tfs <- gettable("tfsummary")
#tfd <- gettable("tfdata")
#simtime <- gettable("simtime")
aconf <- gettable("agent_config")
aconf$uuid <- with(aconf, paste(r2(sessionid), agentid, sep='.'))
pglall <- adduuid(gettable("pglog"))
pglall <- merge(pglall, aconf[,c('sessionid','agentid','agenttype','uuid')], by.x=c('sessionid', 'userid', 'uuid'), by.y=c('sessionid', 'agentid', 'uuid'))
pglall <- arrange(pglall, rowid)    # ensure pglall is sorted in chronological order
ts <- gettable('teamstatus')
ts$uuid <- with(ts, paste(r2(sessionid), agentid, sep='.'))
ts$iternum <- ts$internum   ## STUPID DATABASE TYPO!

pglall$keep[pglall$keep == -1] = NA
pglall$contrib[pglall$contrib == -1] = NA
pglall$pctcontrib = with(pglall, contrib / (contrib + keep))
pgl <- subset(pglall, agenttype=='human')

nbrlist <- adduuid(gettable("neighborlist"))
# Count the number of neighbors by user and round
nbrs <- adduuid(dbGetQuery(con, "SELECT COUNT(neighbor) AS numnbrs, GROUP_CONCAT(neighbor) as neighbors, * from neighbors group by sessionid, simnum, userid"))
nbrs <- subset(nbrs, !(sessionid %in% badses))
nbrs$condition <- ses_cond_tab[nbrs$sessionid]

nbrsbig <- adduuid(gettable("neighbors"))

tflr <- merge(tfl, rs[,3:length(rs)], by=c('sessionid', 'eventtype', 'simnum', 'iternum', 'userid', 'otherid', 'uuid', 'condition'), all.x=T)
tflr <- arrange(tflr, rowid)


## Fix the NAs in rating step
# There are only a few ratings with a zero eframe; I think we'll just ignore those for now. And only 3 are NA
# This is inefficient, but we'll try it
rtg <- adduuid(gettable("ratings"))
#levels(rtg$step)[levels(rtg$step)=='publicgoods'] = 'pubgood'
rtg$step[rtg$step=='publicgoods'] = 'pubgood'   # Should not be necessary, but is...
rtg$step <- factor(rtg$step, levels=c('apply', 'acceptvote', 'join', 'pubgood', 'pg_postprocess', 'NA'), ordered=TRUE)   # rearrange
rtg$step[is.na(rtg$step)] = 'NA'    # Not sure why I need this, but ok.
rtg$stepfix <- rtg$step
rtg$stepfix2 <- as.character(rtg$step)
rtg$waiting <- (rtg$step == 'NA')
for (i in 1:nrow(rtg)) {
  row = rtg[i,]
  #if (!is.na(row$step) | row$eframe == 0) next
  if (row$step != 'NA' | row$etime == 0) next
  #print(i)
  ebefore <- tail(subset(tfe, uuid==row$uuid & etime < row$etime),n=1)
  if (nrow(ebefore) == 0) next
  #print(ebefore)
  #eafter <- subset(tfe, uuid==row$uuid & sframe > row$sframe)
  #etype = ifelse(ebefore$eventtype=='pubgood', 'pg_postprocess', ebefore$eventtype) 
  etype = ebefore$eventtype
  rtg$stepfix[i] = etype
  rtg$stepfix2[i] = paste(etype,'wait',sep='')
}
rtg$stepraw <- rtg$step
rtg$step <- rtg$stepfix
rtg$stepfix2 <- factor(rtg$stepfix2, levels=c('apply','applywait','acceptvote','acceptvotewait','join','joinwait','pubgood','pubgoodwait','pg_postprocess','NA'), ordered=TRUE)

## Create data about past contributions in pgl and tfl 
# These seem like inelegant ways to do this, but they work!

# Get mean of all past contribs by uuid
pglall$pastmeancontrib <- with(pglall, sapply(1:nrow(pglall), function(i) {m<-mean(pctcontrib[(simnum < simnum[i]) & (uuid==uuid[i])],na.rm=TRUE); ifelse(is.nan(m), NA, m)}))
# Get last contrib by uuid
pglall$lastcontrib <- with(pglall, sapply(1:nrow(pglall), function(i) last(pctcontrib[(simnum < simnum[i]) & (uuid==uuid[i]) & !is.na(pctcontrib)])))
#head(arrange(pglall, sessionid, simnum, userid) %>% select(sessionid, simnum, userid, pctcontrib, pastmeancontrib, lastcontrib), n=50) # Check if it worked

tflpg <- subset(tfl, eventtype=='pubgood')
tflpg$pctcontrib <- with(tflpg, newpay/maxpay)
# Get mean of contrib history for otherid that uuid has seen
tflpg$pastmeancontribknown <- with(tflpg, sapply(1:nrow(tflpg), function(i) {m<-mean(pctcontrib[(simnum < simnum[i]) & (uuid==uuid[i]) & (otherid==otherid[i])],na.rm=TRUE); ifelse(is.nan(m), NA, m)}))
# Get last contrib of otherid that uuid has seen
tflpg$lastcontribknown <- with(tflpg, sapply(1:nrow(tflpg), function(i) last(pctcontrib[(simnum < simnum[i]) & (uuid==uuid[i]) & (otherid==otherid[i]) & !is.na(pctcontrib)])))
pgknown <- aggregate(cbind(pastmeancontribknown, lastcontribknown)~(sessionid+userid+otherid+simnum), tflpg, first)

tflrpg <- merge(tflpg, rs[,c('sessionid', 'eventtype', 'simnum', 'userid', 'otherid', 'uuid','myrtg','globalrtg','minrtg','maxrtg')], by=c('sessionid', 'eventtype', 'simnum', 'userid', 'otherid', 'uuid'), all.x=T)
tflrpg$myrtg[tflrpg$myrtg == -1] = NA
tflrpg$globalrtg[tflrpg$globalrtg == -1] = NA
tflrpg$minrtg[tflrpg$minrtg == -1] = NA
tflrpg$maxrtg[tflrpg$maxrtg == -1] = NA

tflrpge <- tflrpg %>% group_by(sessionid, simnum, userid) %>% summarize(pctcontrib=mean(pctcontrib), globalmean=mean(globalrtg,na.rm=T), mymean=mean(myrtg,na.rm=T), meanmeancontrib=mean(pastmeancontribknown,na.rm=T), meanlastcontrib=mean(lastcontribknown,na.rm=T))


pgratings <- subset(rtg, step=='pg_postprocess')
pgratings2 <- merge(pgratings, pglall, by.x=c('sessionid', 'otherid', 'simnum'), by.y=c('sessionid', 'userid', 'simnum'))


# Construct the finaldata table here
#   Number of neighbors, avg pctcontrib, final pay, etc.
# finaldata <- fp
# contribs <- aggregate(pctcontrib~sessionid+userid, pglall, mean)
# finaldata <- merge(finaldata, contribs, all.x=TRUE)
# nnbrs <- aggregate(numnbrs~sessionid+userid, nbrs, max)
# finaldata <- merge(finaldata, nnbrs, all.x=TRUE)
# finalrats <- merge(subset(rs, eventtype=='final' & myrtg != -1), aconf, by.x=c('sessionid', 'userid'), by.y=c('sessionid','agentid'))
# meanhumanrats <- aggregate(myrtg~sessionid+otherid, subset(finalrats, agenttype=='human'), namean)
# meanhumanrats <- rename(meanhumanrats, meanhumanrtg=myrtg)
# finaldata <- merge(finaldata, meanhumanrats, by.x=c('sessionid', 'userid'), by.y=c('sessionid', 'otherid'), all.x=TRUE)
# meanmyrats <- aggregate(myrtg~sessionid+userid, subset(finalrats, agenttype=='human'), namean)
# meanmyrats <- rename(meanmyrats, meanmyrtgs=myrtg)
# finaldata <- merge(finaldata, meanmyrats, all.x=TRUE)
# 
# finaldata$payperround <- with(finaldata, as.numeric(pay/table(tfs$sessionid)[as.character(sessionid)]))
# 
# # Merge on z-scores of everything
# numscale <- function(x) {as.numeric(scale(x))}
# finaldata <- finaldata %>% group_by(sessionid) %>% mutate(zpay=numscale(pay), znbrs=numscale(numnbrs), zrtg=numscale(meanhumanrtg), zmyrtg=numscale(meanmyrtgs), zcontrib=numscale(pctcontrib), zppr=numscale(payperround)) %>% ungroup()





## USER BEHAVIOR STATS/SIMULATOR

# Here, we want to build a sim agent which will act like the real human subjects
# We can probably just calculate a lot of conditional probabilities to define an agent

# Things we need:
#  condition
#  timing?
#  TF decisions
#  pubgoods decisions

# We'll need some method of dealing with NAs
# Strategy:  figure based on contributions, if available. Otherwise, factor in global rating, if available. Else, take the average.

# condition
ucond <- select(intr, uuid, condition)


# team formation decisions:

tflrc <- tflr %>% left_join(pgknown) %>% mutate(deltapay=newpay-currentpay, ismax=newpay==maxpay)

tflnohist <- tflrc %>% group_by(uuid) %>%
  filter(globalrtg==-1 | is.na(globalrtg), is.na(pastmeancontribknown)) 

uapplynohist <- tflnohist %>% filter(eventtype=='apply') %>% summarize(apply_nohist=namean(chosen))
uacceptnohist <- tflnohist %>% filter(eventtype=='acceptvote', otherid != -1) %>% summarize(acceptvote_nohist=namean(chosen))
unoaccept <- tflnohist %>% filter(eventtype=='acceptvote', otherid == -1, currentpay < maxpay) %>% summarize(acceptvote_noaccept=namean(chosen))
ustayaccept <- tflnohist %>% filter(eventtype=='acceptvote', otherid == -1, currentpay == maxpay) %>% summarize(acceptvote_stayaccept=namean(chosen))
ujoinnohist <- tflnohist %>% filter(eventtype=='join' & otherid != -1) %>% summarize(join_nohist=namean(chosen))

ggplot(subset(tflrc, eventtype=='apply' & is.na(pastmeancontribknown)), aes(x=chosen, y=globalrtg, group=uuid)) + facet_grid(~ismax)+geom_point() + geom_smooth(method='lm', se=F) # This looks not that relevant

uapplydeltapay <- tflrc %>% group_by(uuid) %>% filter(eventtype=='apply', globalrtg==-1, is.na(pastmeancontribknown)) %>% 
  do(applypaylm=tryna(glm(chosen~deltapay, data=., na.action=na.omit, family=binomial))) %>%
  mutate(apply_deltapay_intercept=tryna(summary(applypaylm)$coeff[1]), 
         apply_deltapay_slope=tryna(summary(applypaylm)$coeff[2]), 
         apply_deltapay_aic=tryna(summary(applypaylm)$aic)) %>%
  select(-applypaylm)

uapplyglo <- tflrc %>% group_by(uuid) %>% filter(eventtype=='apply', is.na(pastmeancontribknown)) %>% 
  do(applyglolm=tryna(glm(chosen~globalrtg+deltapay, data=., na.action=na.omit, family=binomial))) %>%
  mutate(apply_globalrtg_intercept=tryna(summary(applyglolm)$coeff[1]), 
         apply_globalrtg_slope=tryna(summary(applyglolm)$coeff[2]),
         apply_globalrtg_slope_pay=tryna(summary(applyglolm)$coeff[3]), 
         apply_globalrtg_aic=tryna(summary(applyglolm)$aic)) %>%
  select(-applyglolm)
# This really doesn't look all that useful...

uapplycontrib <- tflrc %>% group_by(uuid) %>% filter(eventtype=='apply') %>% 
  do(applycontlm=tryna(glm(chosen~pastmeancontribknown+deltapay, data=., na.action=na.omit, family=binomial))) %>%
  mutate(apply_pastcontrib_intercept=tryna(summary(applycontlm)$coeff[1]), 
         apply_pastcontrib_slope=tryna(summary(applycontlm)$coeff[2]), 
         apply_pastcontrib_slope_pay=tryna(summary(applycontlm)$coeff[3]), 
         apply_pastcontrib_aic=tryna(summary(applycontlm)$aic)) %>%
  select(-applycontlm)


# applyX <- subset(tflrc, eventtype=='apply') %>% mutate(deltapay=newpay-currentpay, ismax=newpay==maxpay)
# summary(glm(chosen~globalrtg+(deltapay), data=subset(applyX, is.na(pastmeancontribknown) & uuid=='01.0')))
# ## Basically, this shows that global rating is completely irrelevant in apply (for 01.0)
# 
# summary(glm(chosen~globalrtg+(deltapay), data=subset(applyX, is.na(pastmeancontribknown) & uuid=='02.0'), family=binomial))
# summary(glm(chosen~globalrtg+(deltapay), data=subset(applyX, is.na(pastmeancontribknown) & uuid=='03.0'), family=binomial))
# ## Pretty much holds up
# 
# summary(glm(chosen~pastmeancontribknown+(deltapay), data=subset(applyX, uuid=='01.0'), family=binomial))
# summary(glm(chosen~pastmeancontribknown+(deltapay), data=subset(applyX, uuid=='02.0'), family=binomial))
# summary(glm(chosen~pastmeancontribknown+(deltapay), data=subset(applyX, uuid=='03.0'), family=binomial))


median(uapplydeltapay$applypay_aic)
median(uapplyglo$applyglo_aic)        ## really doesn't add much from just deltapay
median(uapplycontrib$applycontrib_aic)


# Acceptvote and join will be trickier, because we need a utility function to rank options, rather than considering them independently
# We could, however, perhaps, just train glm(s), and pick the option with the highest probability
  
uacceptdeltapay <- tflrc %>% group_by(uuid) %>% filter(eventtype=='acceptvote', is.na(pastmeancontribknown), globalrtg==-1) %>% 
  do(acceptpaylm=tryna(glm(chosen~deltapay, data=., na.action=na.omit, family=binomial))) %>%
  mutate(acceptvote_deltapay_intercept=tryna(summary(acceptpaylm)$coeff[1]), 
         acceptvote_deltapay_slope=tryna(summary(acceptpaylm)$coeff[2]), 
         acceptvote_deltapay_aic=tryna(summary(acceptpaylm)$aic)) %>%
  select(-acceptpaylm)

uacceptdeltapay2 <- tflrc %>% group_by(uuid) %>% filter(eventtype=='acceptvote', is.na(pastmeancontribknown), globalrtg==-1) %>% 
  mutate(noaccept=otherid==-1) %>%
  do(acceptpaylm=tryna(glm(chosen~deltapay+noaccept, data=., na.action=na.omit, family=binomial))) %>%
  mutate(acceptvote_deltapay_intercept=tryna(summary(acceptpaylm)$coeff[1]), 
         acceptvote_deltapay_slope=tryna(summary(acceptpaylm)$coeff[2]),
         acceptvote_deltapay_slope_noaccept=tryna(summary(acceptpaylm)$coeff[3]), 
         acceptvote_deltapay_aic=tryna(summary(acceptpaylm)$aic)) %>%
  select(-acceptpaylm)
# A modest improvement over not including the noaccept column, but not much
  
uacceptglo <- tflrc %>% group_by(uuid) %>% filter(eventtype=='acceptvote', is.na(pastmeancontribknown)) %>% 
  do(acceptglolm=tryna(glm(chosen~globalrtg+deltapay, data=., na.action=na.omit, family=binomial))) %>%
  mutate(acceptvote_globalrtg_intercept=tryna(summary(acceptglolm)$coeff[1]), 
         acceptvote_globalrtg_slope=tryna(summary(acceptglolm)$coeff[2]),
         acceptvote_globalrtg_slope_pay=tryna(summary(acceptglolm)$coeff[3]), 
         acceptvote_globalrtg_aic=tryna(summary(acceptglolm)$aic)) %>%
  select(-acceptglolm)

uacceptcontrib <- tflrc %>% group_by(uuid) %>% filter(eventtype=='acceptvote') %>% 
  do(acceptcontlm=tryna(glm(chosen~pastmeancontribknown+deltapay, data=., na.action=na.omit, family=binomial))) %>%
  mutate(acceptvote_pastcontrib_intercept=tryna(summary(acceptcontlm)$coeff[1]), 
         acceptvote_pastcontrib_slope=tryna(summary(acceptcontlm)$coeff[2]), 
         acceptvote_pastcontrib_slope_pay=tryna(summary(acceptcontlm)$coeff[3]), 
         acceptvote_pastcontrib_aic=tryna(summary(acceptcontlm)$aic)) %>%
  select(-acceptcontlm)

# uacceptglocontrib <- tflrc %>% group_by(uuid) %>% filter(eventtype=='acceptvote') %>% 
#   do(acceptgcontlm=tryna(glm(chosen~pastmeancontribknown+globalrtg+deltapay, data=., na.action=na.omit, family=binomial))) %>%
#   mutate(acceptgcontrib_intercept=tryna(summary(acceptgcontlm)$coeff[1]), 
#          acceptgcontrib_slope_contrib=tryna(summary(acceptgcontlm)$coeff[2]), 
#          acceptgcontrib_slope_grat=tryna(summary(acceptgcontlm)$coeff[3]), 
#          acceptgcontrib_slope_pay=tryna(summary(acceptgcontlm)$coeff[4]), 
#          acceptgcontrib_aic=tryna(summary(acceptgcontlm)$aic)) %>%
#   select(-acceptgcontlm)

  
median(uacceptdeltapay$acceptpay_aic)
median(uacceptglo$acceptglo_aic)
median(uacceptcontrib$acceptcontrib_aic)
#median(uacceptglocontrib$acceptgcontrib_aic)  ## This doesn't add much; in fact, it's worse
  
  
ujoindeltapay <- tflrc %>% group_by(uuid) %>% filter(eventtype=='join') %>% 
  mutate(staygroup=otherid==-1) %>%
  do(joinpaylm=tryna(glm(chosen~staygroup+deltapay, data=., na.action=na.omit, family=binomial))) %>%
  mutate(join_deltapay_intercept=tryna(summary(joinpaylm)$coeff[1]), 
         join_deltapay_stay=tryna(summary(joinpaylm)$coeff[2]), 
         join_deltapay_slope=tryna(summary(joinpaylm)$coeff[3]), 
         join_deltapay_aic=tryna(summary(joinpaylm)$aic)) %>%
  select(-joinpaylm)

ujoinglo <- tflrc %>% group_by(uuid) %>% filter(eventtype=='join', is.na(pastmeancontribknown)) %>% 
  mutate(staygroup=otherid==-1) %>%
  do(joinglolm=tryna(glm(chosen~staygroup+globalrtg+deltapay, data=., na.action=na.omit, family=binomial))) %>%
  mutate(join_globalrtg_intercept=tryna(summary(joinglolm)$coeff[1]), 
         join_globalrtg_stay=tryna(summary(joinglolm)$coeff[2]), 
         join_globalrtg_slope=tryna(summary(joinglolm)$coeff[3]),
         join_globalrtg_slope_pay=tryna(summary(joinglolm)$coeff[4]), 
         join_globalrtg_aic=tryna(summary(joinglolm)$aic)) %>%
  select(-joinglolm)

## Not enough data to actually use this, I think
# ujoincontrib <- tflrc %>% group_by(uuid) %>% filter(eventtype=='join') %>% 
#   mutate(staygroup=otherid==-1) %>%
#   do(joincontlm=tryna(glm(chosen~staygroup+pastmeancontribknown+deltapay, data=., na.action=na.omit, family=binomial))) %>%
#   mutate(lmlen=length(joincontlm)) %>% filter(lmlen > 1) %>%
#   mutate(joincontrib_intercept=tryna(summary(joincontlm)$coeff[1]), 
#          joincontrib_stay=tryna(summary(joincontriblm)$coeff[2]), 
#          joincontrib_slope=tryna(summary(joincontlm)$coeff[3]), 
#          joincontrib_slope_pay=tryna(summary(joincontlm)$coeff[4]), 
#          joincontrib_aic=tryna(summary(joincontlm)$aic)) %>%
#   select(-joincontlm)
# 
# ujoinglocontrib <- tflrc %>% group_by(uuid) %>% filter(eventtype=='join') %>% 
#   mutate(staygroup=otherid==-1) %>%
#   do(joingcontlm=tryna(glm(chosen~staygroup+pastmeancontribknown+globalrtg+deltapay, data=., na.action=na.omit, family=binomial))) %>%
#   mutate(lmlen=length(joingcontlm)) %>% filter(lmlen > 1) %>%
#   mutate(joingcontrib_intercept=tryna(summary(joingcontlm)$coeff[1]), 
#          joingcontrib_stay=tryna(summary(joingcontlm)$coeff[2]), 
#          joingcontrib_slope_contrib=tryna(summary(joingcontlm)$coeff[3]), 
#          joingcontrib_slope_grat=tryna(summary(joingcontlm)$coeff[4]), 
#          joingcontrib_slope_pay=tryna(summary(joingcontlm)$coeff[5]), 
#          joingcontrib_aic=tryna(summary(joingcontlm)$aic)) %>%
#   select(-joingcontlm)

median(ujoindeltapay$join_deltapay_aic)
median(ujoinglo$join_globalrtg_aic)
#median(ujoincontrib$joincontrib_aic)
#median(ujoinglocontrib$joingcontrib_aic)
## TODO: FIX THIS UP SO THIS WORKS WITH JOIN!
  
# test the predictions
jtest <- tflrc %>% filter(eventtype=='join', uuid == '01.0') %>% mutate(staygroup=otherid==-1)
jglm <- glm(chosen~staygroup+globalrtg+deltapay, data=jtest, na.action=na.omit, family=binomial)
jtest$cpred <- predict(jglm, jtest, type='response')
jtest$choose <- jtest$cpred > 0.5
select(jtest, uuid, staygroup, globalrtg, deltapay, chosen, choose, cpred)
table(jtest$chosen==jtest$choose)
#  do(joinglolm=tryna(glm(chosen~staygroup+globalrtg+deltapay, data=., na.action=na.omit))) %>%
  
  
# pubgoods postprocess rating decisions
# get coefficients
ggplot(pgratings2, aes(pctcontrib, rating, group=uuid.x)) + geom_point() + geom_smooth(method='lm', se=F)
uppgrat <- pgratings2 %>% group_by(uuid.x) %>% 
  do(ratlm=lm(as.numeric(rating)~pctcontrib, data=.)) %>%
  mutate(pubgood_rating_contrib_intercept=summary(ratlm)$coeff[1], 
         pubgood_rating_contrib_slope=summary(ratlm)$coeff[2], 
         pubgood_rating_contrib_stderr=summary(ratlm)$sigma,
         pubgood_rating_contrib_r2=summary(ratlm)$adj.r.squared) %>%
  mutate(uuid=uuid.x) %>%
  select(-ratlm, -uuid.x)
# Will want some way to deal with missing/silly data

# Calculate the proportion of each kind of rating that someone gives
#table(rating)
# Use this as the null if r2 is bad
uppgratnull <- rtg %>% group_by(uuid=uuid) %>%
  summarize(
    pubgood_pct1=mean(rating==1),
    pubgood_pct2=mean(rating==2),
    pubgood_pct3=mean(rating==3),
    pubgood_pct4=mean(rating==4),
    pubgood_pct5=mean(rating==5))


# Ratings-per-round
nrounds <- with(tfs, data.frame(table(sessionid)))
nrounds$sessionid <- as.numeric(as.character(nrounds$sessionid))
#uppgratfreq <- pgratings2 %>% left_join(nrounds) %>% group_by(uuid=uuid.x) %>% 
#  summarize(pubgood_ratings_per_round=n()/max(Freq))

uuidses <- with(pgl, data.frame(table(uuid, sessionid, simnum))) %>% filter(Freq > 0) %>% mutate(simnum=as.numeric(as.character(simnum)), sessionid=as.numeric(as.character(sessionid)), uuid.x=uuid) %>% select(-Freq, -uuid)

uppgratfreq <- uuidses %>% left_join(nrounds) %>% left_join(pgratings2) %>% 
  group_by(uuid=uuid.x, Freq, simnum) %>% 
  summarize(nrats=length(unique(na.omit(uuid.y)))) %>% 
  summarize(pubgood_ratings_per_round=sum(nrats)/max(Freq), 
            pubgood_ratings_per_round_sd=sd(nrats),
            pubgood_prop_rounds_nrats_0=sum(nrats==0)/max(Freq)) %>%
  select(-Freq)
# To get an accurate sd, we may need to insert zeros for rounds with no ratings...
# The issue is that these are all SO skewed - we almost need probability of zero, and then some simple stat to determine likelihood of more ratings.
# Or like fit an exponential distribution with given mean and sd

test1 <- uuidses %>% left_join(nrounds) %>% left_join(pgratings2) %>% 
  group_by(uuid=uuid.x, Freq, simnum) %>% 
  summarize(nrats=length(unique(na.omit(uuid.y))))
# for (u in unique(test1$uuid)) {
#   hist(subset(test1, uuid==u)$nrats, main=u, right=T)
#   readline()
# }
# Yes. there are a lot of zeros
round(prop.table(table(test1$uuid,test1$nrats), 1),2)[,'0']


# Several ways to calculate a contribution

ucontribavgs <- pgl %>% group_by(uuid) %>% summarize(pubgood_avgcontrib=namean(pctcontrib), pubgood_sdcontrib=sd(pctcontrib, na.rm=T))

ggplot(adduuid(tflrpge), aes(globalmean, pctcontrib, group=uuid)) + geom_point() + geom_smooth(method='lm', se=F)
ggplot(adduuid(tflrpge), aes(meanmeancontrib, pctcontrib, group=uuid)) + geom_point() + geom_smooth(method='lm', se=F)
ummccontrib <- adduuid(tflrpge) %>% group_by(uuid) %>% 
  do(mmccontriblm=tryna(lm(pctcontrib~meanmeancontrib, data=., na.action=na.omit))) %>%
  mutate(pubgood_contrib_pastcontrib_intercept=tryna(summary(mmccontriblm)$coeff[1]), 
         pubgood_contrib_pastcontrib_slope=tryna(summary(mmccontriblm)$coeff[2]), 
         pubgood_contrib_pastcontrib_stderr=tryna(summary(mmccontriblm)$sigma), 
         pubgood_contrib_pastcontrib_r2=tryna(summary(mmccontriblm)$adj.r.squared)) %>%
  select(-mmccontriblm) # -mmccontriblm

## Something is wrong with this
# ugratcontrib <- adduuid(tflrpge) %>% group_by(uuid) %>% 
#   do(ratcontriblm=tryna(lm(pctcontrib~globalmean, data=., na.action=na.omit))) %>%
#   mutate(lmlen=length(ratcontriblm)) %>%
#   filter(lmlen > 1) %>%
#   mutate(pubgood_contrib_globalrtg_intercept=ratcontriblm$coefficients[1], 
#          pubgood_contrib_globalrtg_slope=tryna(ratcontriblm$coefficients[2]), 
#          pubgood_contrib_globalrtg_r2=tryna(summary(ratcontriblm)$adj.r.squared)) %>%
#   select(-ratcontriblm, -lmlen)
## All of the models come out NA; I do not know why
## This is exactly the same code as the above, but for some reason, we get "$ operator is invalid for atomic vectors"

# adduuid(tflrpge) %>% group_by(uuid) %>% 
#   do(ratcontriblm=tryna(lm(pctcontrib~meanmeancontrib, data=., na.action=na.omit))) %>%
#   mutate(lmlen=length(ratcontriblm)) %>%
#   filter(lmlen > 1) %>%
#   mutate(athing=ratcontriblm$coeff[1])
# ## ERROR: $ operator is invalid for atomic vectors
# 
# adduuid(tflrpge) %>% group_by(uuid) %>% 
#   do(ratcontriblm=tryna(lm(pctcontrib~meanmeancontrib, data=., na.action=na.omit))) %>%
#   mutate(lmlen=length(ratcontriblm)) %>%
#   filter(lmlen > 1) %>%
#   mutate(athing=ratcontriblm$coeff[1])

## I can't get that to work via dplyr, so here goes manual.
getcoeff1 <- function(x) {tryna(x$coeff[1])}
getcoeff2 <- function(x) {tryna(x$coeff[2])}
getr2 <- function(x) {tryna(summary(x)$adj.r.squared)}
getstderr <- function(x) {tryna(summary(x)$sigma)}

ugratcontrib <- adduuid(tflrpge) %>% group_by(uuid) %>% 
  do(ratcontriblm=tryna(lm(pctcontrib~globalmean, data=., na.action=na.omit))) %>%
  mutate(lmlen=length(ratcontriblm)) %>%
  filter(lmlen > 1)
ugratcontrib$pubgood_contrib_globalrtg_intercept <- sapply(ugratcontrib$ratcontriblm, getcoeff1)
ugratcontrib$pubgood_contrib_globalrtg_slope <- sapply(ugratcontrib$ratcontriblm, getcoeff2)
ugratcontrib$pubgood_contrib_globalrtg_r2 <- sapply(ugratcontrib$ratcontriblm, getr2)
ugratcontrib$pubgood_contrib_globalrtg_stderr <- sapply(ugratcontrib$ratcontriblm, getstderr)
ugratcontrib <- select(ugratcontrib, -ratcontriblm, -lmlen)

# umyratcontrib <- adduuid(tflrpge) %>% group_by(uuid) %>% 
#   do(myratcontriblm=tryna(lm(pctcontrib~mymean, data=., na.action=na.omit))) %>%
#   mutate(lmlen=length(myratcontriblm)) %>%
#   filter(lmlen > 1) %>%
#   mutate(myratcontrib_intercept=tryna(summary(myratcontriblm)$coeff[1]), 
#          myratcontrib_slope=tryna(summary(myratcontriblm)$coeff[2]), 
#          myratcontrib_r2=tryna(summary(myratcontriblm)$adj.r.squared)) %>%
#   select(-myratcontriblm, -lmlen)



# timing
ggplot(subset(tfe, eventtype=='apply' & elapsed < 100), aes(simnum, elapsed, group=uuid)) + geom_point() + geom_smooth(method='lm', se=F)
utiming <- tfe %>% group_by(condition, sessionid, uuid, eventtype) %>%
  filter(elapsed < 100) %>%
  do(timelm=tryna(lm(elapsed~simnum+iternum, data=.))) %>%
  mutate(timing_intercept=tryna(summary(timelm)$coeff[1]), 
         timing_simnum_slope=tryna(summary(timelm)$coeff[2]),
         timing_iternum_slope=tryna(summary(timelm)$coeff[3]), 
         timing_r2=tryna(summary(timelm)$adj.r.squared)) %>%  
  select(-timelm)
# Linear models do not appear to fit the data well
  
utiming2 <- tfe %>% group_by(condition, sessionid, uuid, eventtype) %>%
  filter(elapsed < 100) %>%
  summarize(time_avg=mean(elapsed),
         time_sd=sd(elapsed),
         time_med=median(elapsed),
         time_iqr=IQR(elapsed),
         time_q1=quantile(elapsed,0.25),
         time_q3=quantile(elapsed,0.75))
# This will need to be flattened, and we will need to pick which metrics we want, because each user is only getting one line in the final data file.

utimingtest <- utiming2 %>% group_by(uuid, eventtype, time_q1, time_q3) %>%
  do(repdat=rnorm(1000, mean=.$time_avg, sd=.$time_sd)) %>%
  mutate(iniqr=mean(repdat > time_q1 & repdat < time_q3),
         ltzero=mean(repdat < 0)) %>%
  select(-repdat)
#hist(utimingtest$ltzero)
#hist(utimingtest$iniqr)
# Hm. This suggests the median-based metrics may be superior

# use dcast to flatten this out into columns
# ex: dcast(utiming2, uuid~eventtype, value.var='time_q1')
flattime <- function(df,var,suffix) {
  utflat <- dcast(df, uuid~eventtype, value.var=var)
  names(utflat) <- sapply(names(utflat), FUN=function(n) paste(n,suffix, sep='_'))
  names(utflat)[1] <- 'uuid'
  utflat
}
utime_q1 <- flattime(utiming2, 'time_q1', 'time_q1')
utime_med <- flattime(utiming2, 'time_med', 'time_med')
utime_q3 <- flattime(utiming2, 'time_q3', 'time_q3')

# List of things to merge
alltables <- list(
ucond,

uapplynohist,
uapplydeltapay,
uapplycontrib,

uacceptnohist,
unoaccept,
ustayaccept,
uacceptdeltapay,
uacceptglo,
uacceptcontrib,

ujoinnohist,
ujoindeltapay,
ujoinglo,

ummccontrib,
ugratcontrib,
#umyratcontrib,
ucontribavgs,

uppgrat,
uppgratfreq,
uppgratnull,

utime_q1,
utime_med,
utime_q3
)

userdatatable <- Reduce(function(x, y) merge(x, y, all=TRUE), alltables)
write.csv(userdatatable, 'userdatatable.csv', row.names=F)
names(userdatatable)


# Tests:
userdatatable %>% mutate(pnh=round(apply_nohist,2),
                         pn5=round(logoddstoprob(apply_deltapay_intercept-5*apply_deltapay_slope),2),
                         p0=round(logoddstoprob(apply_deltapay_intercept),2), 
                         pp5=round(logoddstoprob(apply_deltapay_intercept+5*apply_deltapay_slope),2)) %>%
                  select(uuid, pnh, pn5, p0, pp5)

userdatatable %>% mutate(pnh=round(acceptvote_nohist,2),
                         pn5=round(logoddstoprob(acceptvote_deltapay_intercept-5*acceptvote_deltapay_slope),2),
                         p0=round(logoddstoprob(acceptvote_deltapay_intercept),2), 
                         pp5=round(logoddstoprob(acceptvote_deltapay_intercept+5*acceptvote_deltapay_slope),2)) %>%
                  select(uuid, pnh, pn5, p0, pp5)

userdatatable %>% mutate(pnh=round(join_nohist,2),
                         pn5=round(logoddstoprob(join_deltapay_intercept-5*join_deltapay_slope),2),
                         p0=round(logoddstoprob(join_deltapay_intercept),2), 
                         pp5=round(logoddstoprob(join_deltapay_intercept+5*join_deltapay_slope),2)) %>%
                  select(uuid, pnh, pn5, p0, pp5)

userdatatable %>% mutate(pnh=round(join_nohist,2),
                         pn5=round(logoddstoprob(join_deltapay_intercept-5*join_deltapay_slope),2),
                         p0=round(logoddstoprob(join_deltapay_intercept),2), 
                         pp5=round(logoddstoprob(join_deltapay_intercept+5*join_deltapay_slope),2),
                         pn5s=round(logoddstoprob(join_deltapay_intercept-5*join_deltapay_slope+join_deltapay_stay),2),
                         p0s=round(logoddstoprob(join_deltapay_intercept+join_deltapay_stay),2), 
                         pp5s=round(logoddstoprob(join_deltapay_intercept+5*join_deltapay_slope+join_deltapay_stay),2)) %>%
                  select(uuid, pnh, pn5, pn5s, p0, p0s, pp5, pp5s)
