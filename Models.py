# from gen_ped import gen_ped
from ast import literal_eval
import sys
import random
from ExportImage import exportImage

class Simulation:
    '''
    This class handles the main simulation events 
    '''

    def __init__(self, mp = "omaha", state='sleep',time_elapsed=0):
        self.state=state
        self.time_elapsed=time_elapsed
        self.map = mp

    def warmup(self):
        '''
        handles initial random generation and loading the documents
        '''
        self.steps = 0
        self.bunkers = []
        self.cells = []
        random.seed(100) # use the same seed every time
        self.loadDoc()

         # ships linked list
        self.shipCount = 0
        self.shipHead = None
        self.shipTail = None

        # soldiers linked list
        self.soldierCount = 0
        self.soldierHead = None
        self.soldierTail = None

        # generators linked list
        self.genCount = 0
        self.genHead = None
        self.genTail = None

        self.deadSoldierCount = 0
        self.margin = 100

        return

    def loadDoc(self):
        
        bunkerFile = open("image/" + self.map + "_target.txt")
        bid = 4
        for line in bunkerFile:
            tmp = Bunker(bid - 4, literal_eval(line))
            self.bunkers.append(tmp)
            bid += 1

        mapfile = open("image/" + self.map + ".txt")
        row = 0
        for line in mapfile:
            col = 0
            tmp = line.split(" ")[:-1]
            row_cell = []
            for t in tmp:
                ctype = int(t)
                cell = Cell(row, col, -1, ctype)
                row_cell.append(cell)
                col+=1
            row+=1
            self.cells.append(row_cell)

        self.width = len(self.cells[0])
        self.hasShip = [False] * self.width

        conefile = open("image/" + self.map + "_cone.txt")

        bid = 4
        for line in conefile:
            coords = line.split(";")[:-1]
            for c in coords:
                cone = literal_eval(c)
                self.cells[cone[1]][cone[0]].cone = bid - 4
            bid+=1

        # print(self.cells)

        return
    
    def run_simulation(self):
        self.state='running'
        self.steps = 0
        self.ped_count = 0
        print ('simulation starts')
        self.execute()
        return

    def bunkersLeft(self):
        for b in self.bunkers:
            if b.dead == False:
                return True
        return False

    def execute(self):
        while(self.bunkersLeft() == True and self.deadSoldierCount < 5000):
            self.step()
        
        self.stop_simulation()
    
    def step(self):

        if self.steps % 200 == 0:
            print (str(self.soldierCount)+" soldiers left.")
            print (str(self.deadSoldierCount)+" soldiers killed.")

        # generate ships
        if self.steps % 20 == 0:
            for i in range(5):
                rng = random.randint(self.margin, self.width - self.margin)
                while self.hasShip[rng]:
                    rng = random.randint(self.margin, self.width - self.margin)
                self.hasShip[rng] = True

                tmp = Ship(-1, rng, 0, -1)
                if self.shipHead == None:
                    self.shipHead = tmp
                    self.shipTail = tmp
                else:
                    self.shipTail.next = tmp
                    tmp.prev = self.shipTail
                    self.shipTail = tmp
                self.shipCount += 1

        # move ships and check if ships arrive
        s = self.shipHead
        while s != None:
            if self.cells[s.unit_y][s.unit_x].cell_type != 0:
                tmp = Generator(s.unit_x, s.unit_y)
                if self.genHead == None:
                    self.genHead = tmp
                    self.genTail = tmp
                else:
                    self.genTail.next = tmp
                    tmp.prev = self.genTail
                    self.genTail = tmp

                self.hasShip[s.unit_x] = False

                tmp = s.next
                if s == self.shipHead:
                    self.shipHead = s.next
                if s == self.shipTail:
                    self.shipTail = s.prev
                if s.prev != None:
                    s.prev.next = s.next
                if s.next != None:
                    s.next.prev = s.prev
                s.prev = None
                s.next = None
                del s
                s = tmp
                self.shipCount -= 1
                continue
            else:
                s.unit_y += 5
                s = s.next

        # generate soldiers
        g = self.genHead
        while g != None:
            if self.cells[g.unit_y][g.unit_x].walkable == 1:
                tmp = Soldier(-1, g.unit_x, g.unit_y, self.bunkers)
                if self.soldierHead == None:
                    self.soldierHead = tmp
                    self.soldierTail = tmp
                else:
                    self.soldierTail.next = tmp
                    tmp.prev = self.soldierTail
                    self.soldierTail = tmp
                self.cells[tmp.unit_y][tmp.unit_x].walkable = 0
                self.soldierCount += 1
                g.numSoldier -= 1

            if g.numSoldier <= 0:
                tmp = g.next
                if g == self.genHead:
                    self.genHead = g.next
                if g == self.genTail:
                    self.genTail = g.prev
                if g.prev != None:
                    g.prev.next = g.next
                if g.next != None:
                    g.next.prev = g.prev
                g.prev = None
                g.next = None
                del g
                g = tmp
                self.genCount -= 1
                continue

            g = g.next


        # move soldiers
        s = self.soldierHead
        while s != None:

            # refind target
            if self.bunkers[s.target].dead == True:
                s.findTarget(self.bunkers)

            # move to new cell
            s.move(self.cells, self.bunkers)
            cur_cell = self.cells[s.unit_y][s.unit_x]
            
            # attacked by bunker
            if cur_cell.cone > -1 and self.bunkers[cur_cell.cone].dead == False:
                if(random.random() > 0.95):
                    s.health -= random.randint(1, 3) # (5, 15)

            # attack bunker
            if cur_cell.cell_type > 3 and self.bunkers[cur_cell.cell_type-4].dead == False:
                if(random.random() > 0.05):
                    s.health -= random.randint(10, 30) # (5, 15)
                if(random.random() > 0.95):
                    self.bunkers[cur_cell.cell_type - 4].health -= random.randint(1, 3)

            # check if soldier dies
            if s.health <= 0:
                self.cells[s.unit_y][s.unit_x].walkable = 1
                tmp = s.next
                if s == self.soldierHead:
                    self.soldierHead = s.next
                if s == self.soldierTail:
                    self.soldierTail = s.prev
                if s.prev != None:
                    s.prev.next = s.next
                if s.next != None:
                    s.next.prev = s.prev
                s.prev = None
                s.next = None
                del s
                s = tmp
                self.soldierCount -= 1
                self.deadSoldierCount += 1
                continue

            s = s.next

        # check if bunker down
        for b in self.bunkers:
            if b.health <= 0 and b.dead == False:
                b.dead = True
                print ("bunker "+str(cur_cell.cell_type)+" is dead.")
                print (str(self.soldierCount)+" soldiers left.")
                print (str(self.deadSoldierCount)+" soldiers killed.")


        # output data
        if self.steps % 10 == 0:

            testfi2 = open("images2/test" + str(int(self.steps / 10)) + '.csv', 'w')
            temp = self.soldierHead
            while temp != None:
                testfi2.write(str(temp.unit_x)+','+str(temp.unit_y)+'\n')
                temp = temp.next
            testfi2.close()

            testfi3 = open("images2/ship" + str(int(self.steps / 10)) + '.csv', 'w')
            temp = self.shipHead
            while temp != None:
                testfi3.write(str(temp.unit_x)+','+str(temp.unit_y)+'\n')
                temp = temp.next
            testfi3.close()

            exportImage(int(self.steps / 10), self.map)

        self.steps += 1

        return
        

    def stop_simulation(self):
        self.state='stopped'
        print ('simulation over')
        print ('battle lasted: '+str(self.steps)+' seconds')
        if self.soldierCount <= 50:
            print("Germans win. Damn!")
        else:
            print("Allies win!")


class Cell(object):
    def __init__(self,x_pos,y_pos,cellID, cell_type, walkable=1):
        self.x_pos=x_pos
        self.y_pos=y_pos
        self.cellID=cellID   #seperate CellID and genID and TargetID, so that we can loop through them seperately
        self.cell_type=cell_type
        self.walkable=walkable #only cell has walkability, cuz there is no obstacle cells in the csv file
        # self.neighbors = neighbors
        # self.FFs = FFs
        self.cone = -1

class Generator(object):
    def __init__(self, unit_x, unit_y):
        self.unit_x = unit_x
        self.unit_y = unit_y
        self.numSoldier = 30
        self.prev = None
        self.next = None

class Land(Cell):
    def __init__(self, height, *args): 
        super(Land, self).__init__(*args)
        self.height = height

class Bunker:
    def __init__(self, bID, center):
        self.bID = bID
        self.health = 1000
        self.center = center
        self.dead = False
        
     
class Soldier: 
    def __init__(self, sID, unit_x, unit_y, targets):
        self.sID = sID
        self.unit_x=unit_x
        self.unit_y=unit_y

        self.likeability = []

        #randomize attributes here
        self.speed = 0
        self.health = 100
        self.injured = False
        self.morale = 100

        self.stay = 0 #count turns stayed

        self.findTarget(targets)

        self.prev = None
        self.next = None

    def findTarget(self, targets):
        distance = 999999
        self.target = -1
        for t in targets:
            if t.dead == True:
                continue
            newd = pow((t.center[0] - self.unit_x), 2) + pow((t.center[1] - self.unit_y), 2)
            if newd < distance:
                distance = newd
                self.target = t.bID

    def move(self, cells, targets):
        dx = float(targets[self.target].center[0] - self.unit_x)
        dy = float(targets[self.target].center[1] - self.unit_y)
        dxa = abs(dx)
        dya = abs(dy)
        probs = [0.0] * 8
        maxDiagProb = 0.6 # Tunable
        randomProb = 0.5 # Tunable
        repulsion = 0.8 # repulsion for the cone
        width = len(cells[0])
        height = len(cells)

        if dxa == 0 and dya == 0:
            return

        pd = maxDiagProb * 2 * min(dxa, dya) / (dxa + dya)
        if dx < dy:
            px = (1 - maxDiagProb - randomProb) * dxa / (dxa + dya)
            py = 1 - randomProb - pd - px
        else:
            py = (1 - maxDiagProb - randomProb) * dya / (dxa + dya)
            px = 1 - randomProb - pd - py

        nx = self.unit_x
        ny = self.unit_y

        if dx >= 0 and dy >= 0:
            tmpx = nx+1
            tmpy = ny+1
            if tmpx < height and tmpy < width and cells[tmpy][tmpx].cone > -1 and targets[cells[tmpy][tmpx].cone].dead == False:
                pd *= repulsion
            if tmpx < height and cells[ny][tmpx].cone > -1 and targets[cells[ny][tmpx].cone].dead == False:
                px *= repulsion
            if tmpy < width and cells[tmpy][nx].cone > -1 and targets[cells[tmpy][nx].cone].dead == False:
                py *= repulsion
            probs[7] = pd
            probs[4] = px
            probs[6] = py
        elif dx >= 0 and dy < 0:
            tmpx = nx+1
            tmpy = ny-1
            if tmpx < height and tmpy >= 0 and cells[tmpy][tmpx].cone > -1 and targets[cells[tmpy][tmpx].cone].dead == False:
                pd *= repulsion
            if tmpx < height and cells[ny][tmpx].cone > -1 and targets[cells[ny][tmpx].cone].dead == False:
                px *= repulsion
            if tmpy >= 0 and cells[tmpy][nx].cone > -1 and targets[cells[tmpy][nx].cone].dead == False:
                py *= repulsion
            probs[2] = pd
            probs[4] = px
            probs[1] = py
        elif dx < 0 and dy < 0:
            tmpx = nx-1
            tmpy = ny-1
            if tmpx >= 0 and tmpy >= 0 and cells[tmpy][tmpx].cone > -1 and targets[cells[tmpy][tmpx].cone].dead == False:
                pd *= repulsion
            if tmpx >= 0 and cells[ny][tmpx].cone > -1 and targets[cells[ny][tmpx].cone].dead == False:
                px *= repulsion
            if tmpy >= 0 and cells[tmpy][nx].cone > -1 and targets[cells[tmpy][nx].cone].dead == False:
                py *= repulsion
            probs[0] = pd
            probs[3] = px
            probs[1] = py
        elif dx < 0 and dy >= 0:
            tmpx = nx-1
            tmpy = ny+1
            if tmpx >= 0 and tmpy < width and cells[tmpy][tmpx].cone > -1 and targets[cells[tmpy][tmpx].cone].dead == False:
                pd *= repulsion
            if tmpx >= 0 and cells[ny][tmpx].cone > -1 and targets[cells[ny][tmpx].cone].dead == False:
                px *= repulsion
            if tmpy < width and cells[tmpy][nx].cone > -1 and targets[cells[tmpy][nx].cone].dead == False:
                py *= repulsion
            probs[5] = pd
            probs[3] = px
            probs[6] = py

        for i in range(10):
            rng = random.randint(0, 7)
            probs[rng] += randomProb / 10

        cdf = [probs[0]]
        for i in range(1, len(probs)):
            cdf.append(cdf[-1] + probs[i])
        for e in cdf:
            e /= cdf[-1]
        rng = random.random()
        for i in range(8):
            decision = i
            if rng < cdf[i]:
                break

        if decision == 0:
            nx = self.unit_x - 1
            ny = self.unit_y - 1
        elif decision == 1:
            ny = self.unit_y - 1
        elif decision == 2:
            nx = self.unit_x + 1
            ny = self.unit_y - 1
        elif decision == 3:
            nx = self.unit_x - 1
        elif decision == 4:
            nx = self.unit_x + 1
        elif decision == 5:
            nx = self.unit_x - 1
            ny = self.unit_y + 1
        elif decision == 6:
            ny = self.unit_y + 1
        elif decision == 7:
            nx = self.unit_x + 1
            ny = self.unit_y + 1

        if cells[ny][nx].walkable != 0:
            cells[self.unit_y][self.unit_x].walkable = 1;
            self.unit_x = nx
            self.unit_y = ny
            cells[self.unit_y][self.unit_x].walkable = 0;

class Ship:
    def __init__(self, shipID, unit_x, unit_y, armyID):
        self.unit_x=unit_x
        self.unit_y=unit_y
        self.shipID = shipID
        self.armyID = armyID

        self.prev = None
        self.next = None

class Turret:
    def __init__(self, tID, damage):
        self.tID = tID
        self.damage = damage
    
class Formulae:
    def calc_targetcomp(self,p):
        return

    
    
    