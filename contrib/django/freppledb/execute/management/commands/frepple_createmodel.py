#
# Copyright (C) 2007 by Johan De Taeye
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation; either version 2.1 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser
# General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#

#  file     : $URL$
#  revision : $LastChangedRevision$  $LastChangedBy$
#  date     : $LastChangedDate$

import random
from optparse import make_option
from datetime import timedelta, datetime, date

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.conf import settings
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User

from input.models import *
from common.models import Dates
from execute.models import log


class Command(BaseCommand):

  help = '''
      This script is a simple, generic model generator.
      This test script is meant more as a sample for your own tests on
      evaluating performance, memory size, database size, ...

      The autogenerated supply network looks schematically as follows:
        [ Operation -> buffer ] ...   [ -> Operation -> buffer ]  [ Delivery ]
        [ Operation -> buffer ] ...   [ -> Operation -> buffer ]  [ Delivery ]
        [ Operation -> buffer ] ...   [ -> Operation -> buffer ]  [ Delivery ]
        [ Operation -> buffer ] ...   [ -> Operation -> buffer ]  [ Delivery ]
        [ Operation -> buffer ] ...   [ -> Operation -> buffer ]  [ Delivery ]
            ...                                  ...
      Each row represents a cluster.
      The operation+buffer are repeated as many times as the depth of the supply
      path parameter.
      In each cluster a single item is defined, and a parametrizable number of
      demands is placed on the cluster.
    '''

  option_list = BaseCommand.option_list + (
      make_option('--user', dest='user', type='string',
        help='User running the command'),
      make_option('--cluster', dest='cluster', type="int",
        help='Number of end items'),
      make_option('--demand', dest='demand', type="int",
        help='Demands per end item'),
      make_option('--forecast_per_item', dest='forecast_per_item', type="int",
        help='Monthly forecast per end item'),
      make_option('--level', dest='level', type="int",
        help='Depth of bill-of-material'),
      make_option('--resource', dest='resource', type="int",
        help='Number of resources'),
      make_option('--resource_size', dest='resource_size', type="int",
        help='Size of each resource'),
      make_option('--components', dest='components', type="int",
        help='Total number of components'),
      make_option('--components_per', dest='components_per', type="int",
        help='Number of components per end item'),
      make_option('--deliver_lt', dest='deliver_lt', type="int",
        help='Average delivery lead time of orders'),
      make_option('--procure_lt', dest='procure_lt', type="int",
        help='Average procurement lead time'),
      make_option('--currentdate', dest='currentdate', type="string",
        help='Current date of the plan in YYYY-MM-DD format')
  )

  requires_model_validation = False

  def get_version(self):
    return settings.FREPPLE_VERSION


  @transaction.commit_manually
  def handle(self, **options):
    # Make sure the debug flag is not set!
    # When it is set, the django database wrapper collects a list of all sql
    # statements executed and their timings. This consumes plenty of memory
    # and cpu time.
    tmp_debug = settings.DEBUG
    settings.DEBUG = False

    # Pick up the options
    if 'verbosity' in options: verbosity = int(options['verbosity'] or '1')
    else: verbosity = 1
    if 'user' in options: user = options['user']
    else: user = ''
    if 'cluster' in options: cluster = int(options['cluster'] or '100')
    else: cluster = 100
    if 'demand' in options: demand = int(options['demand'] or '30')
    else: demand = 30
    if 'forecast_per_item' in options: forecast_per_item = int(options['forecast_per_item'] or '50')
    else: forecast_per_item = 50
    if 'level' in options: level = int(options['level'] or '5')
    else: level = 5
    if 'resource' in options: resource = int(options['resource'] or '60')
    else: resource = 60
    if 'resource_size' in options: resource_size = int(options['resource_size'] or '5')
    else: resource_size = 5
    if 'components' in options: components = int(options['components'] or '200')
    else: components = 200
    if 'components_per' in options: components_per = int(options['components_per'] or '5')
    else: components_per = 5
    if 'deliver_lt' in options: deliver_lt = int(options['deliver_lt'] or '30')
    else: deliver_lt = 30
    if 'procure_lt' in options: procure_lt = int(options['procure_lt'] or '40')
    else: procure_lt = 40
    if 'currentdate' in options: currentdate = options['currentdate'] or '2009-01-01'
    else: currentdate = '2009-01-01'

    random.seed(100) # Initialize random seed to get reproducible results
    cnt = 100000     # A counter for operationplan identifiers

    # Pick up the startdate
    try:
      startdate = datetime.strptime(currentdate,'%Y-%m-%d')
    except Exception, e:
      raise CommandError("current date is not matching format YYYY-MM-DD")

    # Check whether the database is empty
    if Buffer.objects.count()>0 or Item.objects.count()>0:
      raise CommandError("Database must be empty before creating a model")

    try:
      # Logging the action
      log(
        category='CREATE', theuser=user,
        message = u'%s : %d %d %d %d %d %d %d %d %d %d'
          % (_('Start creating sample model with parameters'),
             cluster, demand, forecast_per_item, level, resource,
             resource_size, components, components_per, deliver_lt,
             procure_lt)
        ).save()

      # Plan start date
      if verbosity>0: print "Updating plan..."
      try:
        p = Plan.objects.all()[0]
        p.currentdate = startdate
        p.save()
      except:
        # No plan exists yet
        p = Plan(name="frePPLe", currentdate=startdate)
        p.save()

      # Update the user horizon
      try:
        userprofile = User.objects.get(username=user).get_profile()
        userprofile.startdate = startdate.date()
        userprofile.enddate = (startdate + timedelta(365)).date()
        userprofile.save()
      except:
        pass # It's not important if this fails

      # Planning horizon
      # minimum 10 daily buckets, weekly buckets till 40 days after current
      if verbosity>0: print "Updating horizon telescope..."
      updateTelescope(10, 40)

      # Working days calendar
      if verbosity>0: print "Creating working days..."
      workingdays = Calendar.objects.create(name="Working Days",type= "calendar_boolean")
      weeks = Calendar.objects.create(name="Weeks")
      cur = None
      cur2 = None
      for i in Dates.objects.all():
        curdate = datetime(i.day_start.year, i.day_start.month, i.day_start.day)
        dayofweek = int(curdate.strftime("%w")) # day of the week, 0 = sunday, 1 = monday, ...
        if dayofweek == 1:
          # A bucket for the working week: monday through friday
          if cur:
            cur.enddate = curdate
            cur.save()
          if cur2:
            cur2.enddate = curdate
            cur2.save()
          cur = Bucket(startdate=curdate, value=1, calendar=workingdays)
          cur2 = Bucket(startdate=curdate, value=1, calendar=weeks)
        elif dayofweek == 6:
          # A bucket for the weekend
          if cur:
            cur.enddate = curdate
            cur.save()
          if cur2:
            cur2.enddate = curdate
            cur2.save()
          cur = Bucket(startdate=curdate, value=0, calendar=workingdays)
          cur2 = Bucket(startdate=curdate, value=0, calendar=weeks)
      if cur: cur.save()
      if cur2: cur2.save()
      transaction.commit()

      # Create a random list of categories to choose from
      categories = [ 'cat A','cat B','cat C','cat D','cat E','cat F','cat G' ]

      # Create customers
      if verbosity>0: print "Creating customers..."
      cust = []
      for i in range(100):
        c = Customer.objects.create(name = 'Cust %03d' % i)
        cust.append(c)
      transaction.commit()

      # Create resources and their calendars
      if verbosity>0: print "Creating resources and calendars..."
      res = []
      for i in range(resource):
        loc = Location(name='Loc %05d' % int(random.uniform(1,cluster)))
        loc.save()
        cal = Calendar(name='capacity for res %03d' %i, category='capacity')
        bkt = Bucket(startdate=startdate, value=resource_size, calendar=cal)
        cal.save()
        bkt.save()
        r = Resource.objects.create(name = 'Res %03d' % i, maximum=cal, location=loc)
        res.append(r)
      transaction.commit()
      random.shuffle(res)

      # Create the components
      if verbosity>0: print "Creating raw materials..."
      comps = []
      comploc = Location.objects.create(name='Procured materials')
      for i in range(components):
        it = Item.objects.create(name = 'Component %04d' % i, category='Procured')
        ld = abs(round(random.normalvariate(procure_lt,procure_lt/3)))
        c = Buffer.objects.create(name = 'Component %04d' % i,
             location = comploc,
             category = 'Procured',
             item = it,
             type = 'buffer_procure',
             min_inventory = 20,
             max_inventory = 100,
             size_multiple = 10,
             leadtime = str(ld * 86400),
             onhand = str(round(forecast_per_item * random.uniform(1,3) * ld / 30)),
             )
        comps.append(c)
      transaction.commit()

      # Loop over all clusters
      durations = [ 86400, 86400*2, 86400*3, 86400*5, 86400*6 ]
      for i in range(cluster):
        if verbosity>0: print "Creating supply chain for end item %d..." % i

        # location
        loc, created = Location.objects.get_or_create(name='Loc %05d' % i)
        loc.available = workingdays
        loc.save()
        
        # Item and delivery operation
        oper = Operation.objects.create(name='Del %05d' % i, sizemultiple=1, location=loc)
        it = Item.objects.create(name='Itm %05d' % i, operation=oper, category=random.choice(categories))

        # Forecast
        fcst = Forecast.objects.create( \
          name='Forecast item %05d' % i,
          calendar=workingdays,
          item=it,
          maxlateness=60*86400, # Forecast can only be planned 2 months late
          priority=3, # Low priority: prefer planning orders over forecast
          )

        # This method will take care of distributing a forecast quantity over the entire
        # horizon, respecting the bucket weights.
        fcst.setTotal(startdate, startdate + timedelta(365), forecast_per_item * 12)

        # Level 0 buffer
        buf = Buffer.objects.create(name='Buf %05d L00' % i,
          item=it,
          location=loc,
          category='00'
          )
        fl = Flow.objects.create(operation=oper, thebuffer=buf, quantity=-1)

        # Demand
        for j in range(demand):
          dm = Demand.objects.create(name='Dmd %05d %05d' % (i,j),
            item=it,
            quantity=int(random.uniform(1,6)),
            # Exponential distribution of due dates, with an average of deliver_lt days.
            due = startdate + timedelta(days=round(random.expovariate(float(1)/deliver_lt/24))/24),
            # Orders have higher priority than forecast
            priority=random.choice([1,2]),
            customer=random.choice(cust),
            category=random.choice(categories)
            )

        # Create upstream operations and buffers
        ops = []
        for k in range(level):
          if k == 1 and res:
            # Create a resource load for operations on level 1
            oper = Operation.objects.create(name='Oper %05d L%02d' % (i,k),
              type='operation_time_per',
              location=loc,
              duration_per=86400,
              sizemultiple=1,
              )
            if resource < cluster and i < resource:
              # When there are more cluster than resources, we try to assure
              # that each resource is loaded by at least 1 operation.
              Load.objects.create(resource=res[i], operation=oper)
            else:
              Load.objects.create(resource=random.choice(res), operation=oper)
          else:
            oper = Operation.objects.create(
              name='Oper %05d L%02d' % (i,k),
              duration=random.choice(durations),
              sizemultiple=1,
              location=loc,
              )
          ops.append(oper)
          buf.producing = oper
          # Some inventory in random buffers
          if random.uniform(0,1) > 0.8: buf.onhand=int(random.uniform(5,20))
          buf.save()
          Flow(operation=oper, thebuffer=buf, quantity=1, type="flow_end").save()
          if k != level-1:
            # Consume from the next level in the bill of material
            buf = Buffer.objects.create(
              name='Buf %05d L%02d' % (i,k+1),
              item=it,
              location=loc,
              category='%02d' % (k+1)
              )
            Flow.objects.create(operation=oper, thebuffer=buf, quantity=-1)

        # Consume raw materials / components
        c = []
        for j in range(components_per):
          o = operation = random.choice(ops)
          b = random.choice(comps)
          while (o,b) in c:
            # A flow with the same operation and buffer already exists
            o = operation = random.choice(ops)
            b = random.choice(comps)
          c.append( (o,b) )
          fl = Flow.objects.create(
            operation = o, thebuffer = b,
            quantity = random.choice([-1,-1,-1,-2,-3]))

        # Commit the current cluster
        transaction.commit()

      # Log success
      log(category='CREATE', theuser=user,
        message=_('Finished creating sample model')).save()

    except Exception, e:
      # Log failure and rethrow exception
      try: log(category='CREATE', theuser=user,
        message=u'%s: %s' % (_('Failure creating sample model'),e)).save()
      except: pass
      raise CommandError(e)

    finally:
      # Commit it all, even in case of exceptions
      transaction.commit()
      settings.DEBUG = tmp_debug


@transaction.commit_manually
def updateTelescope(min_day_horizon=10, min_week_horizon=40):
  '''
  Update for the telescopic horizon.
  The first argument specifies the minimum number of daily buckets. Additional
  daily buckets will be appended till we come to a monday. At that date weekly
  buckets are starting.
  The second argument specifies the minimum horizon with weeks before the
  monthly buckets. The last weekly bucket can be a partial one: starting on
  monday and ending on the first day of the next calendar month.
  '''

  # Make sure the debug flag is not set!
  # When it is set, the django database wrapper collects a list of all sql
  # statements executed and their timings. This consumes plenty of memory
  # and cpu time.
  tmp_debug = settings.DEBUG
  settings.DEBUG = False

  first_date = Dates.objects.all()[0].day_start
  current_date = Plan.objects.all()[0].currentdate
  limit = current_date + timedelta(min_day_horizon)
  mode = 'day'
  try:
    m = []
    for i in Dates.objects.all():
      if i.day_start < current_date:
        # A single bucket for all dates in the past
        i.standard = 'past'
        i.standard_start = first_date
        i.standard_end = current_date
      elif mode == 'day':
        # Daily buckets
        i.standard = str(i.day_start.date())[2:]  # Leave away the leading century, ie "20"
        i.standard_start = i.day_start
        i.standard_end = i.day_end
        if i.day_start >= limit and i.dayofweek == 0:
          mode = 'week'
          limit = (current_date + timedelta(min_week_horizon)).date()
          limit = datetime(limit.year+limit.month/12, limit.month+1-12*(limit.month/12), 1)
      elif i.day_start < limit:
        # Weekly buckets
        i.standard = i.week
        i.standard_start = i.week_start
        i.standard_end = (i.week_end > limit and limit) or i.week_end
      else:
        # Monthly buckets
        i.standard = i.month
        i.standard_start = i.month_start
        i.standard_end = i.month_end
      m.append(i)
    # Needed to create a temporary list of the objects to save, since the
    # database table is locked during the iteration
    for i in m: i.save()
    transaction.commit()
  finally:
    transaction.rollback()
    settings.DEBUG = tmp_debug
