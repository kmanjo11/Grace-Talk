The DCMA 14-Point Assessment

Logic – Is the schedule logical? Schedule logic involves schedule tasks; Are all the predecessor, successor tasks concurrent? Missing links need to be resolved because without schedule logic an accurate Critical Path will not be possible.

Leads – are not allowed in scheduling as they are confusing and disrupt the flow of the schedule. Leads are often replaced with positive lags, but this isn’t always the best alternative. It is better to have shorter known scopes of work tasks connected by FS relationships, with no lags.

Lags – The DCMA does allow positive lags but has set a limit for use in a schedule. The limit for lags is no more than 5% of activity relationships. The best option is to replace lags with tasks describing the effort or process, such as cure time. Lags are limited to 5% in order to support schedule clarity.

FS Relationships – Even though Primavera P6 and Deltek Acumen Fuse both support all relationship types, the DCMA assessment states 90% (or more) of schedule dependencies should be Finish-Start (FS). Start-Start (SS) are acceptable, but building a whole schedule using SS is obviously unacceptable.

Hard Constraints – can really affect logic and disable a schedule from being logic driven. The DCMA assessment states that hard constraints should be limited to 5% of uncompleted tasks. Constraints of any type are discouraged and a schedule should work without any.

High Float – activities may not be linked properly and can cause stress on the Critical Path. Total Float values are limited to 44 days, therefore review tasks that have greater than 2 months total float and limit their usage to 5% of incomplete tasks.

Negative Float – Schedules that have negative float tasks are already behind. Ideally the DCMA says avoid having negative float in your schedule. If there is negative float, make sure it is accompanied with a documented plan to mitigate being late.

High Duration Tasks – Limit long duration tasks to 5% of incomplete tasks. Task durations should be no longer than two months in order to support schedule updating and reporting efforts. Break long activities down into a series of shorter ones for more detail.

Invalid Dates – Forecasted (future work) work should not be in the past and actual (completed work) work should not be in the future. Invalid dates are not allowed under any circumstance; this will avoid illogical situations where future work is planned for the past and completed work happened in the future.

Resources – Resource loading is not a requirement, but the DCMA like schedules to be resource and cost-loaded. If you follow this path make sure the resource loaded schedule is completely loaded. All activities except milestones must have a cost or associated resource.

Missed Tasks – This check looks at how many activities have finished late compared to the baseline date, monitoring excessive slippage. Only 5% of activities can slip from their finish baseline dates. This metric is a conservative and retrospective measure of schedule progress, but it’s a good generic check to see if your project will deliver on time or not.

Critical Path Test – ensures the schedule has one continuous linkage from project start to finish. It tests the integrity of a schedule’s Critical Path, looking for fluidity driven by good logic linking.

Critical Path Length Index – the Critical Path Length Index (CPLI) is a forward looking gauge that assesses required efficiency to complete the project on schedule. It measures the ratio of the project critical path length and the project total float to the project critical path length. The critical path length is the time in work days from the current date to the completion of the project. The target number is 1.0 and schedule’s that have a CLPI less than 0.95 require further review.

Baseline Execution Index – the Baseline Execution Index (BEI) is an early warning indicator that a schedule is in trouble of not meeting the deadline. Most scheduling software doesn’t have a BEI variable, but it is possible to compute the ratio yourself or purchase an additional scheduling software supplement. The BEI ratios advanced, nontrivial, and purposeful warning makes the computation worth the effort. A BEI of 1.0 means that the schedule is on the right track.


--------


Summary
The DCMA 14-Point assessment is a rigorous set of schedule quality guidelines. Schedules submitted to the DoD have to pass this assessment before projects are approved. Although this assessment was originally introduced for DoD schedules, it has become an industry standard metric and is a useful resource for understanding best scheduling practices.

The advantages of applying the DCMA 14-Point assessment to your own schedule are numerous. Schedulers will avoid common pitfalls which can encroach on the quality of their schedules. Auditing your own schedule by using the tools offered in Deltek Acumen Fuse, makes the assessment user friendly.

The assessment will also ensure that the schedule is well documented and logically complete. By documenting the schedule, you will be explaining each metric so that clarity is increased for both you and the project team. This can also give confidence to senior management and the stakeholders.

