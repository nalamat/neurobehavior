==========================
Positive Behavior Paradigm
==========================

Experiment structure
====================

Note::
    We use two sets of terms interchangeably: reaction and response, score and
    response.  In the Python code (and in most documentation), the correct term
    is a reaction followed by a response, in the RPvds circuit it's a response
    followed by a score.  Eventually the RPvds circuit tags will need to be
    updated to be consistent with the Python code.

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
        ] Denotes maximum possible extent of window

On each trial the duration for nose poke (tag:poke_dur_n) is randomly selected
from the range [`poke_duration_lb`, `poke_duration_ub`).  The subject must
maintain the nose poke for the given duration: i.e. it is non-cumulative, if the
subject withdraws his nose early, the timer resets.  Once the poke duration is
met, the token is presented.  For the trial to be scored, the subject can only
withdraw from the nose poke during the reaction window (i.e. a "response" window
in the RPvds circuit).  

The reaction window begins after `reaction_delay` (tag:resp_del_n) with a fixed
duration `reaction_duration` (tag:resp_dur_n).  All durations and delays are
relative to the start of the trial (i.e. onset of the token).  If the subject
withdraws from the nose poke before or after the reaction window, then the trial
is not scored and the subject does not recieve a reward.  This window provides a
mechanism for requiring a nose-poke to be maintained for a minimum period
following stimulus onset.

When the subject withdraws from the nose-poke during the reaction window (i.e.
a "score" window in the RPvds circuit), they trigger a fixed-duration response
window (tag:score_dur_n): during this window the subject must provide his answer
by going to the spout or initiating a new nose-poke.  The token may continue to
play for a specified duration once the nose-poke is withdrawn
(tag:signal_offset_del_n).  To end the token as soon as the poke is withdrawn,
set `signal_offset_delay` to 0.

Why not just fold the response window into the reaction window?  They
represent two actions the subject must perform: 1) withdrawing from the nose
poke and 2) providing a response.  As the name implies, the reaction window
defines when we want the gerbil to react to the signal: i.e. can they withdraw
immediately, or do we want them to wait until after the token is over?  Once
they have withdrawn, we provide them with a fixed-duration response window that
is triggered when they leave the nose-poke: this ensures they have the same
amount of time to provide their response regardless of whether they left the
nose-poke at the beginning of the reaction window or the end.

If they go to the spout during a GO trial, they can drink for the specified
`reward_duration` (tag:reward_dur_n).  If it's a NOGO trial, a timeout of
duration `timeout_duration` (tag:to_dur_n) is triggered.

TTLs in circuit
---------------

    trial_start
        Start a trial
    trial_reset
        Trial is over, reset all TTLs to low
    POKE_END
        Gerbil withdrew from nose-poke
    GO?
        If true, current trial is a GO, NOGO otherwise
    POKE!!!
        Minimum poke duration has been met
    trial_start_del
        Not used?

    poke_TTL
        High if gerbil is in nose-poke
    spout_TTL
        High if gerbil is on spout
    signal_TTL
        Play sound token
    score_TTL (i.e. the response window)
        Window during which the gerbil must provide a response (either a
        nose-poke or go to the spout).  If the response is provided after this
        window is over, the trial is not scored.
    reward_TTL
        Window during which the gerbil can recieve its reward on a GO trial
    resp_TTL (i.e. the reaction window)
        Window during which gerbil is allowed to withdraw from nose-poke and
        trigger the score TTL

    TO_TTL
        Timeout is active
    int_dur_n
        Minimum intertrial duration

Buffers in circuit
------------------

    go_buf
        GO signal
    nogo_buf
        NOGO signal
    TTL
        The state of up to six TTL lines are compressed into a single 8-bit
        integer which is further compressed into a 32-bit word.  Each of the
        first six bits of the integer indicate the logic level of the TTL.  For
        example, if the first two TTLs are high and the remaining four TTLs are
        low, the binary representation is 000011, or 3 in decimal notation.
        Likewise, if the lines are 001010, the decimal
        notation is 8.  See `cns.pipeline.int_to_TTL` and
        `cns.util.binary_funcs.int_to_TTL`.

Tags in circuit
---------------
    
    resp_dur_n (eventually will be react_dur_n)
        Duration of reaction window
    signal_dur_n
        Maximum duration of tken
    signal_offset_del_n
        Delay following withdraw from nose-poke before turning token off
    score_dur_n (eventually will be resp_dur_n)
        Duration of response window
    reward_dur_n
        Duration of reward window (drinking from spout)
    to_dur_n
        Duration of timeout
    contact_method
        0: touch 1, 1: touch 2, 2: optical 1, 3: optical 2
    TTL_nPer
        Sample status of TTL lines every n samples and save to buffer

    trial_start_ts
        Timestamp of the start of the trial that was just presented
    trial_end_ts
        Timestamp of the end of the trial that was just presented

    trial_start_idx
        Number of times a trial has started
    trial_end_idx
        Number of times a trial has ended

    spout_smooth_n
        Smooth spout signal

Triggers in circuit
-------------------

    soft 1
        Start next trial
    soft 2
        Next trial is a GO (be sure to fire before soft 1)

Potential subject actions
-------------------------

1. Actions when there's no trial
   a. Spout contact
   b. Nose-poke and withdraw before trial onset

2. Actions during a trial
   a. Failure to withdraw during reaction window
   b. Withdraw but failure to go to spout or repoke during response window
   c. Withdraw and repoke during response window [*]_
   d. Withdraw and goto spout during response window

.. [*] Repokes during the intertrial period are ignored

Detection of actions
--------------------

trial = response ^ score ^ reward

1a = spout & !trial
1b = ???
2a = trial & !score
2c = ???
2d = trial & reward


Current scoring rules
---------------------

Actions 1a, 1b, and 2b are not included in computation of hit and false alarm
rate.  During a nogo trial, 2c indicates a correct reject and 2d indicates a
false alarm.  During a GO trial, 2d indicates a hit and 2c indicates a miss.
Note that all subject actions are saved in the trial log so you may choose to
reanalyze them.
