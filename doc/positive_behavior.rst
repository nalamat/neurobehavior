==========================
Positive Behavior Paradigm
==========================

Equipment configuration
=======================

====== ======== ======= ========= ======
RX6 ID Bit Mask PP24 ID Direction Signal
====== ======== ======= ========= ======
0      1        1       OUT       Sync Trigger
1      2        2       IN        Electrical contact 1 (spout)
2      4        3       OUT       LED
3      8        4       IN        Optical 1 (nose poke)
4      16       5       OUT       
5      32       6       IN        
6      64       7       OUT       Pump trigger
7      128      8       IN        
====== ======== ======= ========= ======

Experiment structure
====================

Trial block timeline::

    Nose poke       |-------------------------|
    Spout contact                                       |------------|
    Signal          <==>[--------------------------       ]
    Offset delay                              <===>
    Reaction            <====>[---------------               ]
    Score                                     [---------        ]
    Reward                                              |===========|

    <> Delay
    || Fixed-length window
    [] Variable length window that has a maximum duration but can be shorter if
       a certain event occurs
       -- Denotes actual duration of the window
       ]  Denotes maximum possible extent of window

On each trial the duration for nose poke is randomly selected from the range
defined by `poke_duration_lb` and `poke_duration_ub`.  The subject must
maintain the nose poke for the given duration.  The duration is
non-cumulative: if the subject withdraws his nose early, the timer resets.

Once the subject has maintained his nose poke for the given duration, the
signal is presented.  For the trial to be scored, the subject can only
withdraw from the nose poke during the reaction window.  The reaction window
begins after `reaction_delay` with a fixed duration `reaction_duration`.  If
the subject withdraws from the nose poke before or after the reaction
window, then the trial is not counted.  This window provides a mechanism for
requiring a nose-poke to be maintained for a minimum period following
stimulus onset.

When the subject withdraws from the nose-poke during the reaction window,
they trigger a fixed-duration response window: during this window the
subject must provide his answer by going to the spout or initiating a new
nose-poke. 

Why not just fold the response window into the reaction window?  They
represent two actions the subject must perform: 1) withdrawing from the nose
poke and 2) providing a response.  As the name implies, the reaction window
defines when we want the gerbil to react to the signal.  By providing a
fixed-duration window that is triggered when they leave the nose-poke, we
ensure that they have the same amount of time to provide their response
regardless of whether they left the nose-poke at the beginning of the
reaction window or the end.

NOGO trial

* Go to the spout (false alarm)
* Initiate a new nose-poke (correct reject)

GO trial

* Go to the spout (hit)
* Initiate a new nose-poke (miss)

If the subject does not perform either action, the trial is not scored
(however, the data is saved so one can choose to re-score the trial if they
wish).
